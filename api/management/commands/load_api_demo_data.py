"""
Carga reproducible de datos para la API (Evaluación Sumativa 3).

Un solo comando deja la base lista para la revisión, sin ingresar nada a mano:

    python manage.py load_api_demo_data --password <clave>

Para que la clave no quede en el historial de la terminal, se puede entregar
por variable de entorno (PowerShell):

    $env:API_DEMO_PASSWORD = '<clave>'
    python manage.py load_api_demo_data

Qué hace (en este orden):
  1. Corre seed_sgr (datos base del proyecto: delegaciones, cargos,
     funcionarios, período, catálogo). Se le pasa SIEMPRE la clave indicada,
     así nunca se usa su contraseña por defecto, y su salida se descarta
     porque imprime la clave. Ojo: seed_sgr también crea admin_sgr
     (SUPERUSUARIO), funcionario_demo y verificador_demo; no se usan en las
     pruebas de la API.
  2. Agrega un período cerrado (1-ene a 30-jun de 2026) y las metas por cargo
     y período (los ponderadores de cada cargo suman 100 %).
  3. Crea los grupos api_admin y api_operador y los 3 usuarios de la API:
     api_admin, api_operador y api_sinrol (activos, no staff, no superusuario).
  4. Completa el volumen hasta los mínimos indicados ("top-up"): solo agrega
     lo que falta, así que correrlo de nuevo no duplica ni cambia nada.
  5. Verifica que ningún modelo exigido quede vacío y que el total sea al
     menos --min-total (2.000, lo que pide la rúbrica); si no, falla.

Los 6 modelos exigidos (decisión D1 del plan) son:
  principales  -> Activity, Commitment, Meta, Period
  operacionales -> Evidence, Validation
Si el equipo elige otros, se cambia REQUIRED_MODELS.

Reproducibilidad: con la misma --seed salen los mismos datos. Dos cosas
dependen de la fecha o del azar del sistema y no del seed: el vencimiento de
los compromisos (generate_volume_data lo calcula respecto de hoy) y el nombre
de los archivos de evidencia (llevan un UUID).

Este comando NO modifica seed_sgr ni generate_volume_data: usa los
generadores de este último directamente (en vez de call_command) porque ese
comando solo reparte evidencias entre las actividades que crea en la misma
corrida, y para reponer evidencias hacen falta las ya existentes.
"""
import os
import random
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from api.permissions import GROUP_API_ADMIN, GROUP_API_OPERADOR
from organization.models import Employee, Position
from performance.forms import (
    DECISION_APPROVED,
    DECISION_CORRECTION,
    DECISION_REJECTED,
    VERIFIER_GROUP,
)
from performance.management.commands import generate_volume_data as volume
from performance.models import (
    Activity,
    CatalogItem,
    Commitment,
    Evidence,
    Meta,
    Period,
    Validation,
)

PASSWORD_ENV_VAR = 'API_DEMO_PASSWORD'
MIN_PASSWORD_LENGTH = 8
DEFAULT_SEED = 2026

# Valores por defecto de los mínimos (visibles, o sea sin contar eliminados
# lógicamente). Con ellos los 6 modelos suman 2.168 registros: sobre los 2.000
# que exige la rúbrica, contando solo estos modelos.
DEFAULT_ACTIVITIES = 1600
DEFAULT_EVIDENCES = 300
DEFAULT_COMMITMENTS = 150
DEFAULT_VALIDATIONS = 100
DEFAULT_MIN_TOTAL = 2000

# (nombre, rol en la rúbrica, modelo)
REQUIRED_MODELS = [
    ('Activity', 'principal', Activity),
    ('Commitment', 'principal', Commitment),
    ('Meta', 'principal', Meta),
    ('Period', 'principal', Period),
    ('Evidence', 'operacional', Evidence),
    ('Validation', 'operacional', Validation),
]

# (usuario, grupo o None, qué demuestra)
API_USERS = [
    ('api_admin', GROUP_API_ADMIN, 'lectura y escritura'),
    ('api_operador', GROUP_API_OPERADOR, 'solo lectura'),
    ('api_sinrol', None, 'autenticado sin rol de la API (403 en los recursos)'),
]

# El período que crea seed_sgr y uno cerrado anterior, para que los datos
# abarquen dos períodos.
SEED_PERIOD = {'start_date': date(2026, 7, 1), 'end_date': date(2026, 12, 31)}
CLOSED_PERIOD = {'start_date': date(2026, 1, 1), 'end_date': date(2026, 6, 30)}
CLOSED_PERIOD_DEFAULTS = {
    'computable_days': 181,
    'status': 'Cerrado',
    'amber_threshold': Decimal('70.00'),
    'collective_threshold': Decimal('85.00'),
    'parameters_version': 1,
}

# Metas por cargo (se repiten en cada período). Los ponderadores de cada cargo
# suman exactamente 100 (RN-001) y todos los valores objetivo son > 0 (RN-002).
# (item_name, unit, target_value, weight)
METAS_POR_CARGO = {
    'Encargado de Delegación': [
        ('Informes sociales emitidos', 'informes', '120.00', '40.00'),
        ('Subsidios gestionados', 'subsidios', '200.00', '35.00'),
        ('Derivaciones realizadas', 'derivaciones', '80.00', '25.00'),
    ],
    'Funcionario Municipal': [
        ('Atenciones presenciales', 'atenciones', '400.00', '50.00'),
        ('Seguimientos telefónicos', 'seguimientos', '250.00', '30.00'),
        ('Informes sociales emitidos', 'informes', '60.00', '20.00'),
    ],
    'Verificador de Evidencias': [
        ('Evidencias revisadas', 'evidencias', '300.00', '60.00'),
        ('Revisiones dentro de plazo', 'revisiones', '150.00', '40.00'),
    ],
}

# Reparto de las decisiones de revisión y su efecto en Evidence.review_status
# (Aprobada -> aprobada, igual que la acción "aprobar en lote" del Admin;
# Rechazada -> rechazada; Corrección solicitada -> sigue pendiente).
DECISION_WEIGHTS = [
    (0.70, DECISION_APPROVED, Evidence.REVIEW_STATUS_APROBADA),
    (0.90, DECISION_REJECTED, Evidence.REVIEW_STATUS_RECHAZADA),
    (1.00, DECISION_CORRECTION, Evidence.REVIEW_STATUS_PENDIENTE),
]


@contextmanager
def deterministic(seed):
    """Siembra random y Faker para que la carga sea reproducible y, al
    terminar, deja ambos generadores como estaban: el comando también corre
    dentro de tests y una semilla fija no debe filtrarse a los demás."""
    python_state = random.getstate()
    faker_state = volume.fake.random.getstate()
    random.seed(seed)
    Faker.seed(seed)
    try:
        yield
    finally:
        random.setstate(python_state)
        volume.fake.random.setstate(faker_state)


class Command(BaseCommand):
    help = (
        'Carga reproducible para la API: grupos y usuarios de los roles, '
        'metas, y volumen de datos hasta superar 2.000 registros en los 6 '
        'modelos exigidos. Es idempotente.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            help=(
                'Clave de los usuarios de la API (y de los de seed_sgr). '
                f'Mínimo {MIN_PASSWORD_LENGTH} caracteres. Si se omite se usa '
                f'la variable de entorno {PASSWORD_ENV_VAR}, que evita dejar '
                'la clave en el historial de la terminal.'
            ),
        )
        parser.add_argument(
            '--seed', type=int, default=DEFAULT_SEED,
            help=f'Semilla de los datos aleatorios (por defecto {DEFAULT_SEED}).',
        )
        parser.add_argument(
            '--activities', type=int, default=DEFAULT_ACTIVITIES,
            help=f'Mínimo de actividades al terminar (por defecto {DEFAULT_ACTIVITIES}).',
        )
        parser.add_argument(
            '--evidences', type=int, default=DEFAULT_EVIDENCES,
            help=f'Mínimo de evidencias al terminar (por defecto {DEFAULT_EVIDENCES}).',
        )
        parser.add_argument(
            '--commitments', type=int, default=DEFAULT_COMMITMENTS,
            help=f'Mínimo de compromisos al terminar (por defecto {DEFAULT_COMMITMENTS}).',
        )
        parser.add_argument(
            '--validations', type=int, default=DEFAULT_VALIDATIONS,
            help=f'Mínimo de validaciones al terminar (por defecto {DEFAULT_VALIDATIONS}).',
        )
        parser.add_argument(
            '--min-total', type=int, default=DEFAULT_MIN_TOTAL, dest='min_total',
            help=(
                'Total mínimo entre los 6 modelos para dar la carga por '
                f'válida (por defecto {DEFAULT_MIN_TOTAL}, lo que pide la rúbrica).'
            ),
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        password = self._resolve_password(options['password'])
        targets = {
            Activity: max(0, options['activities']),
            Evidence: max(0, options['evidences']),
            Commitment: max(0, options['commitments']),
            Validation: max(0, options['validations']),
        }
        today = timezone.localdate()

        self.stdout.write('[1/5] Datos base del proyecto (seed_sgr)...')
        # La salida de seed_sgr imprime la clave: se descarta.
        call_command('seed_sgr', password=password, stdout=StringIO())

        with transaction.atomic():
            self.stdout.write('[2/5] Períodos y metas...')
            new_periods, new_metas = self._ensure_periods_and_metas()
            self.stdout.write(f'      +{new_periods} período(s), +{new_metas} meta(s)')

            self.stdout.write('[3/5] Grupos y usuarios de la API...')
            self._ensure_api_users(password)

            self.stdout.write(f'[4/5] Volumen de datos (semilla {options["seed"]})...')
            with deterministic(options['seed']):
                added = self._generate_volume(targets, today)
            self.stdout.write(
                '      +{Activity} actividades, +{Evidence} evidencias, '
                '+{Commitment} compromisos, +{Validation} validaciones'.format(
                    **{model.__name__: n for model, n in added.items()}
                )
            )

        self.stdout.write('[5/5] Verificación')
        rows, total = self._count_required_models()
        self._report(rows, total, options['min_total'])
        self._check(rows, total, options['min_total'])
        self.stdout.write(self.style.SUCCESS('Carga completada.'))

    # ------------------------------------------------------------------
    # Clave
    # ------------------------------------------------------------------
    def _resolve_password(self, option_value):
        password = option_value or os.environ.get(PASSWORD_ENV_VAR)
        if not password:
            raise CommandError(
                'Falta la clave de los usuarios de la API. Indícala con '
                f'--password o con la variable de entorno {PASSWORD_ENV_VAR} '
                '(la variable evita dejarla en el historial de la terminal). '
                'No hay clave por defecto a propósito.'
            )
        if len(password) < MIN_PASSWORD_LENGTH:
            raise CommandError(
                f'La clave debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.'
            )
        return password

    # ------------------------------------------------------------------
    # Períodos y metas
    # ------------------------------------------------------------------
    def _ensure_periods_and_metas(self):
        _, closed_created = Period.objects.get_or_create(
            defaults=CLOSED_PERIOD_DEFAULTS, **CLOSED_PERIOD
        )
        new_periods = int(closed_created)

        periods = [
            Period.objects.filter(**SEED_PERIOD).first(),
            Period.objects.filter(**CLOSED_PERIOD).first(),
        ]
        new_metas = 0
        for position_name, items in METAS_POR_CARGO.items():
            position = Position.objects.filter(name=position_name).first()
            if position is None:
                self.stderr.write(self.style.WARNING(
                    f'      Cargo "{position_name}" no existe: se omiten sus metas.'
                ))
                continue
            for period in filter(None, periods):
                for item_name, unit, target_value, weight in items:
                    if Meta.objects.filter(
                        position=position, period=period, item_name=item_name
                    ).exists():
                        continue
                    meta = Meta(
                        position=position, period=period, item_name=item_name,
                        unit=unit, target_value=Decimal(target_value),
                        weight=Decimal(weight),
                    )
                    try:
                        # Aplica RN-001 y RN-002 (Meta.clean) antes de guardar.
                        meta.full_clean()
                    except ValidationError as exc:
                        self.stderr.write(self.style.WARNING(
                            f'      Meta omitida ({item_name}, {position_name}): '
                            f'{"; ".join(exc.messages)}'
                        ))
                        continue
                    meta.save()
                    new_metas += 1
        return new_periods, new_metas

    # ------------------------------------------------------------------
    # Grupos y usuarios de la API
    # ------------------------------------------------------------------
    def _ensure_api_users(self, password):
        User = get_user_model()
        groups = {
            name: Group.objects.get_or_create(name=name)[0]
            for name in (GROUP_API_ADMIN, GROUP_API_OPERADOR)
        }
        for username, group_name, _ in API_USERS:
            user, created = User.objects.get_or_create(username=username)
            changed = created
            # La clave se escribe solo si es nueva o distinta: con la misma
            # clave, correr de nuevo no modifica nada.
            if created or not user.check_password(password):
                user.set_password(password)
                changed = True
            # Usuarios normales y activos: se fuerza en cada corrida.
            for field, value in (
                ('is_active', True), ('is_staff', False), ('is_superuser', False),
            ):
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    changed = True
            if changed:
                user.save()
            user.groups.set([groups[group_name]] if group_name else [])

    # ------------------------------------------------------------------
    # Volumen
    # ------------------------------------------------------------------
    def _generate_volume(self, targets, today):
        employees = list(Employee.objects.order_by('pk'))
        periods = list(Period.objects.order_by('start_date'))
        attentions = list(
            CatalogItem.objects.filter(category=CatalogItem.CATEGORY_ATTENTION)
            .order_by('name')
        )
        if not employees or not periods or not attentions:
            raise CommandError(
                'seed_sgr no dejó funcionarios, períodos y catálogo; no se '
                'puede generar el volumen.'
            )

        missing = {
            model: max(0, target - model.objects.count())
            for model, target in targets.items()
        }
        generator = volume.Command()

        # Sin metas aquí (lista vacía): el generador las elegiría al azar sin
        # mirar cargo ni período. Se enlazan después, de forma coherente.
        new_activities = generator._generate_activities(
            missing[Activity], employees, periods, [], attentions
        )
        self._link_metas(new_activities)

        # Las evidencias se reparten entre TODAS las actividades existentes, no
        # solo las nuevas: así también se pueden reponer si faltan solas.
        generator._generate_evidences(
            missing[Evidence], list(Activity.objects.order_by('pk'))
        )
        generator._generate_commitments(missing[Commitment], employees)

        added = {
            Activity: len(new_activities),
            Evidence: missing[Evidence],
            Commitment: missing[Commitment],
        }
        added[Validation] = self._generate_validations(missing[Validation], today)
        return added

    def _link_metas(self, activities):
        """Asigna a cada actividad nueva una meta de SU cargo y SU período,
        repartidas en rueda entre las metas de ese cargo."""
        metas = defaultdict(list)
        for meta in Meta.objects.order_by('pk'):
            metas[(meta.position_id, meta.period_id)].append(meta)

        groups = defaultdict(list)
        for activity in activities:
            groups[(activity.employee.position_id, activity.period_id)].append(activity)

        linked = []
        for key, group in groups.items():
            candidates = metas.get(key)
            if not candidates:
                continue
            for index, activity in enumerate(group):
                activity.meta = candidates[index % len(candidates)]
                linked.append(activity)
        Activity.objects.bulk_update(linked, ['meta'], batch_size=500)

    def _generate_validations(self, count, today):
        """Revisiones coherentes con las reglas del formulario de validación:
        las hace un verificador (grupo Verificador), la fecha no es futura ni
        anterior a la de la evidencia, result solo es verdadero si fue
        aprobada y las observaciones son obligatorias si no se aprobó."""
        if count <= 0:
            return 0
        verifier = (
            Employee.objects.filter(user__groups__name=VERIFIER_GROUP)
            .order_by('pk').first()
        )
        if verifier is None:
            raise CommandError(
                f'No hay ningún funcionario del grupo {VERIFIER_GROUP} para '
                'firmar las validaciones (¿falló seed_sgr?).'
            )
        # validation__isnull=True también descarta las evidencias cuya
        # validación fue eliminada lógicamente (siguen ocupando el 1:0..1).
        candidates = list(
            Evidence.objects.filter(validation__isnull=True, date__lte=today)
            .exclude(file='').order_by('code')
        )
        chosen = random.sample(candidates, min(count, len(candidates)))
        for evidence in chosen:
            roll = random.random()
            decision, review_status = next(
                (decision, status) for limit, decision, status in DECISION_WEIGHTS
                if roll < limit
            )
            review_date = min(
                evidence.date + timedelta(days=random.randint(0, 10)), today
            )
            Validation.objects.create(
                evidence=evidence,
                employee=verifier,
                decision=decision,
                date=review_date,
                result=(decision == DECISION_APPROVED),
                notes=volume.fake.sentence(nb_words=8),
                version=1,
            )
            if evidence.review_status != review_status:
                evidence.review_status = review_status
                evidence.save(update_fields=['review_status'])
        return len(chosen)

    # ------------------------------------------------------------------
    # Verificación e informe
    # ------------------------------------------------------------------
    @staticmethod
    def _count_required_models():
        rows = [(name, role, model.objects.count()) for name, role, model in REQUIRED_MODELS]
        return rows, sum(count for _, _, count in rows)

    def _report(self, rows, total, min_total):
        self.stdout.write('')
        self.stdout.write(f'  {"Modelo":<14}{"Rol":<14}{"Registros":>10}')
        self.stdout.write(f'  {"-" * 38}')
        for name, role, count in rows:
            self.stdout.write(f'  {name:<14}{role:<14}{count:>10}')
        self.stdout.write(f'  {"-" * 38}')
        self.stdout.write(
            f'  {"TOTAL":<28}{total:>10}   (mínimo exigido: {min_total})'
        )
        self.stdout.write('')
        self.stdout.write('  Usuarios de la API (la clave es la que indicaste):')
        for username, group_name, meaning in API_USERS:
            self.stdout.write(
                f'    {username:<14}{group_name or "(sin grupo)":<16}{meaning}'
            )
        self.stdout.write(
            '  Nota: seed_sgr también deja admin_sgr (superusuario), '
            'funcionario_demo y verificador_demo con esa misma clave; no se '
            'usan en las pruebas de la API.'
        )
        self.stdout.write('')

    @staticmethod
    def _check(rows, total, min_total):
        problems = []
        empty = [name for name, _, count in rows if count == 0]
        if empty:
            problems.append(f'modelos vacíos: {", ".join(empty)}')
        if total < min_total:
            problems.append(f'el total ({total}) no llega al mínimo ({min_total})')
        if problems:
            raise CommandError('La carga no cumple lo exigido: ' + '; '.join(problems) + '.')
