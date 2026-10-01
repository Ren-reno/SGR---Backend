"""
Fase 8, paso 8.3 -- segundo comando de volumen de datos.

No reemplaza a seed_sgr (ese sigue siendo el que carga los 3 usuarios de
demo y los datos curados para la revisión en vivo). Este comando SOLO
agrega volumen: actividades, evidencias y compromisos adicionales,
generados con Faker, reutilizando los Employee/Period/Meta/CatalogItem
que seed_sgr ya creó -- no crea usuarios ni Delegaciones nuevas.

Nota sobre los valores de status/review_status: el proyecto no tiene una
convención única todavía (ver hallazgo documentado aparte) -- se usa acá
el mismo valor que ya existe como precedente real en el código
(review_status='pendiente', igual al default del modelo; status='Pendiente',
igual al único valor usado en los tests de Fase 3), no un valor inventado
para este comando.

Uso:
    python manage.py generate_volume_data
    python manage.py generate_volume_data --activities 700 --evidences 250 --commitments 50
"""
import io
import random
import uuid

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from faker import Faker
from PIL import Image

from organization.models import Employee
from performance.models import Activity, CatalogItem, Commitment, Evidence, Meta, Period

fake = Faker('es_CL')


class Command(BaseCommand):
    help = "Genera volumen de datos adicional (Fase 8, paso 8.3) sin tocar el seed curado."

    def add_arguments(self, parser):
        parser.add_argument('--activities', type=int, default=700)
        parser.add_argument('--evidences', type=int, default=250)
        parser.add_argument('--commitments', type=int, default=50)

    def handle(self, *args, **options):
        employees = list(Employee.objects.all())
        periods = list(Period.objects.all())
        if not employees or not periods:
            raise CommandError(
                "No hay Employee ni Period cargados todavía. Corre primero "
                "'python manage.py seed_sgr'."
            )
        metas = list(Meta.objects.all())
        attentions = list(
            CatalogItem.objects.filter(category=CatalogItem.CATEGORY_ATTENTION)
        )
        if not attentions:
            raise CommandError(
                "No hay CatalogItem de categoría 'attention' cargados. "
                "Corre primero 'python manage.py seed_sgr'."
            )

        with transaction.atomic():
            activities = self._generate_activities(
                options['activities'], employees, periods, metas, attentions
            )
            self._generate_evidences(options['evidences'], activities)
            self._generate_commitments(options['commitments'], employees)

        total = options['activities'] + options['evidences'] + options['commitments']
        self.stdout.write(self.style.SUCCESS(
            f"Volumen generado: {options['activities']} actividades, "
            f"{options['evidences']} evidencias, {options['commitments']} "
            f"compromisos ({total} registros nuevos)."
        ))

    def _generate_activities(self, count, employees, periods, metas, attentions):
        created = []
        for _ in range(count):
            period = random.choice(periods)
            date = fake.date_between(
                start_date=period.start_date, end_date=period.end_date
            )
            activity = Activity.objects.create(
                employee=random.choice(employees),
                period=period,
                meta=random.choice(metas) if metas else None,
                activity_type=random.choice(
                    ['Primera Atención', 'Seguimiento', 'Cierre de Caso', 'Derivación Externa']
                ),
                service=random.choice(
                    ['Atención Presencial', 'Atención Telefónica', 'Gestión Interna']
                ),
                attention=random.choice(attentions),
                sub_attention=fake.word().capitalize(),
                date=date,
                request_description=fake.sentence(nb_words=12),
                action_taken=fake.sentence(nb_words=10),
                contact_name=fake.name(),
                contact_phone=fake.phone_number(),
                status='Pendiente',
            )
            created.append(activity)
        return created

    def _generate_evidences(self, count, activities):
        if not activities:
            return
        for _ in range(count):
            activity = random.choice(activities)
            Evidence.objects.create(
                activity=activity,
                file=self._fake_image_file(),
                date=activity.date,
                metadata=fake.sentence(nb_words=6),
                review_status='pendiente',
            )

    def _generate_commitments(self, count, employees):
        for _ in range(count):
            employee = random.choice(employees)
            Commitment.objects.create(
                delegation=employee.delegation,
                responsible=employee,
                origin=fake.sentence(nb_words=6),
                requester=fake.name(),
                territory=fake.city(),
                due_date=fake.date_between(start_date='-30d', end_date='+60d'),
                support_area=fake.word().capitalize(),
                status=Commitment.STATUS_INGRESADO,
                observation=fake.sentence(nb_words=8),
            )

    @staticmethod
    def _fake_image_file():
        # PNG 1x1 real y válido, no bytes cualquiera -- así pasa la
        # validación de contenido real de validate_evidence_file (Paso
        # 8.2), no solo la de extensión.
        buffer = io.BytesIO()
        Image.new('RGB', (1, 1), color=(200, 200, 200)).save(buffer, format='PNG')
        return ContentFile(buffer.getvalue(), name=f"{uuid.uuid4()}.png")