"""Pruebas del comando load_api_demo_data (Evaluación Sumativa 3).

Usan mínimos pequeños para correr rápido (con ellos los 6 modelos suman 61
registros). Con los valores por defecto el comando deja 2.168; eso se verifica
corriéndolo a mano, ver su documentación.
"""
import inspect
import os
import random
import shutil
import tempfile
from io import StringIO
from unittest import mock

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from api.management.commands import load_api_demo_data as loader
from api.permissions import GROUP_API_ADMIN, GROUP_API_OPERADOR
from performance.management.commands.seed_sgr import Command as SeedCommand
from performance.models import (
    Activity, Commitment, Evidence, Meta, Period, Validation,
)

User = get_user_model()

# Credencial ficticia, solo para estas pruebas.
PASSWORD = 'Clave-Prueba-2026!'

SMALL = {
    'activities': 30, 'evidences': 6, 'commitments': 4, 'validations': 3,
    'min_total': 50, 'seed': 7,
}
# 30 actividades + 4 compromisos + 16 metas + 2 períodos + 6 evidencias
# + 3 validaciones = 61 registros en los 6 modelos.


def load(**overrides):
    out, err = StringIO(), StringIO()
    options = {**SMALL, 'password': PASSWORD, **overrides}
    call_command('load_api_demo_data', stdout=out, stderr=err, **options)
    return out.getvalue(), err.getvalue()


# Cada carga nueva crea 6 usuarios y el PBKDF2 por defecto domina el tiempo de
# estas pruebas; un hasher rápido solo cambia los tests, no el código.
FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


class LoaderTestMixin:
    """Entorno de las pruebas del cargador: MEDIA_ROOT temporal (las
    evidencias generadas son archivos y no deben ensuciar /media/ del
    proyecto; mismo patrón que performance/tests.py) y hasher rápido."""

    @classmethod
    def setUpClass(cls):
        cls._media = tempfile.mkdtemp()
        cls._override = override_settings(
            MEDIA_ROOT=cls._media, PASSWORD_HASHERS=FAST_HASHERS)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)


class LoadedDataTests(LoaderTestMixin, TestCase):
    """Una sola carga, muchas comprobaciones sobre el resultado."""

    @classmethod
    def setUpTestData(cls):
        cls.stdout, cls.stderr = load()

    # -- salida ---------------------------------------------------------
    def test_output_never_shows_the_password(self):
        self.assertNotIn(PASSWORD, self.stdout)
        self.assertNotIn(PASSWORD, self.stderr)

    def test_output_has_the_table_of_the_six_models(self):
        for name, _, _ in loader.REQUIRED_MODELS:
            self.assertIn(name, self.stdout)
        self.assertIn('TOTAL', self.stdout)
        self.assertIn('Carga completada', self.stdout)

    # -- los 6 modelos --------------------------------------------------
    def test_the_six_required_models_are_populated(self):
        self.assertEqual(Activity.objects.count(), 30)
        self.assertEqual(Evidence.objects.count(), 6)
        self.assertEqual(Commitment.objects.count(), 4)
        self.assertEqual(Meta.objects.count(), 16)
        self.assertEqual(Period.objects.count(), 2)
        # Validation depende de la fecha de hoy (solo se revisan evidencias
        # ya fechadas): basta con que no esté vacío (el seed trae una).
        self.assertGreaterEqual(Validation.objects.count(), 1)
        for name, _, model in loader.REQUIRED_MODELS:
            with self.subTest(model=name):
                self.assertGreater(model.objects.count(), 0)

    def test_every_row_of_the_six_models_passes_full_clean(self):
        for model in (Period, Meta, Activity, Commitment, Evidence, Validation):
            for obj in model.objects.all():
                with self.subTest(model=model.__name__, pk=obj.pk):
                    try:
                        obj.full_clean()
                    except ValidationError as exc:  # pragma: no cover
                        self.fail(f'{model.__name__} {obj.pk} inválido: {exc}')
                    finally:
                        # El validador de Evidence.file abre el archivo.
                        if isinstance(obj, Evidence):
                            obj.file.close()

    def test_evidence_files_exist(self):
        for evidence in Evidence.objects.all():
            with self.subTest(code=evidence.code):
                self.assertTrue(os.path.exists(evidence.file.path))

    # -- usuarios y grupos ----------------------------------------------
    def test_api_users_are_normal_active_users_with_the_right_roles(self):
        expected = {
            'api_admin': [GROUP_API_ADMIN],
            'api_operador': [GROUP_API_OPERADOR],
            'api_sinrol': [],
        }
        for username, groups in expected.items():
            with self.subTest(user=username):
                user = User.objects.get(username=username)
                self.assertTrue(user.is_active)
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)
                self.assertEqual(
                    sorted(user.groups.values_list('name', flat=True)), groups)

    def test_api_users_log_in_with_the_given_password(self):
        for username, _, _ in loader.API_USERS:
            with self.subTest(user=username):
                self.assertIsNotNone(
                    authenticate(username=username, password=PASSWORD))

    def test_the_only_superuser_comes_from_the_web_seed(self):
        # seed_sgr crea admin_sgr (superusuario); el cargador no crea ninguno.
        self.assertEqual(
            list(User.objects.filter(is_superuser=True)
                 .values_list('username', flat=True)),
            ['admin_sgr'])

    def test_api_users_get_tokens_from_the_api(self):
        client = APIClient()
        for username, _, _ in loader.API_USERS:
            with self.subTest(user=username):
                res = client.post(
                    '/api/token/',
                    {'username': username, 'password': PASSWORD},
                    format='json')
                self.assertEqual(res.status_code, 200)
                self.assertIn('access', res.json())

    # -- metas, actividades, validaciones -------------------------------
    def test_metas_follow_the_business_rules(self):
        totals = {}
        for meta in Meta.objects.all():
            self.assertGreater(meta.target_value, 0)
            key = (meta.position_id, meta.period_id)
            totals[key] = totals.get(key, 0) + meta.weight
        # RN-001: los ponderadores de cada cargo y período suman 100 %.
        self.assertEqual(set(totals.values()), {100})

    def test_activities_are_inside_their_period_and_linked_to_coherent_metas(self):
        linked = 0
        for activity in Activity.objects.select_related(
                'period', 'employee', 'meta'):
            with self.subTest(pk=activity.pk):
                period = activity.period
                self.assertTrue(period.start_date <= activity.date <= period.end_date)
                if activity.meta_id:
                    linked += 1
                    self.assertEqual(activity.meta.period_id, activity.period_id)
                    self.assertEqual(
                        activity.meta.position_id, activity.employee.position_id)
        # Las 2 actividades curadas de seed_sgr quedan sin meta a propósito.
        self.assertEqual(linked, 28)

    def test_validations_follow_the_review_rules(self):
        today = timezone.localdate()
        # seed_sgr deja EVID-002 aprobada pero con review_status 'pendiente':
        # solo se exige coherencia en lo que genera el cargador.
        status_for = {
            'Aprobada': Evidence.REVIEW_STATUS_APROBADA,
            'Rechazada': Evidence.REVIEW_STATUS_RECHAZADA,
            'Corrección solicitada': Evidence.REVIEW_STATUS_PENDIENTE,
        }
        for validation in Validation.objects.select_related(
                'evidence', 'employee__user'):
            with self.subTest(pk=validation.pk):
                self.assertTrue(validation.employee.user.groups
                                .filter(name='Verificador').exists())
                self.assertEqual(
                    validation.result, validation.decision == 'Aprobada')
                if validation.decision != 'Aprobada':
                    self.assertTrue(validation.notes.strip())
                self.assertTrue(
                    validation.evidence.date <= validation.date <= today)
                if validation.evidence_id not in ('EVID-001', 'EVID-002'):
                    self.assertEqual(
                        validation.evidence.review_status,
                        status_for[validation.decision])


class ValidationDecisionTests(LoaderTestMixin, TestCase):
    """Con pocos datos el azar podría no generar las tres decisiones; aquí se
    fuerzan para comprobar que cada una deja la validación y su evidencia
    coherentes."""

    @classmethod
    def setUpTestData(cls):
        # Más evidencias que validaciones: quedan candidatas sin revisar.
        load(evidences=12, validations=1)

    def test_each_decision_leaves_validation_and_evidence_coherent(self):
        today = timezone.localdate()
        candidates = Evidence.objects.filter(
            validation__isnull=True, date__lte=today).count()
        self.assertGreaterEqual(candidates, 3, 'faltan evidencias candidatas')
        before = set(Validation.objects.values_list('pk', flat=True))

        # random.random() decide: 0.1 -> Aprobada, 0.8 -> Rechazada,
        # 0.95 -> Corrección solicitada.
        with mock.patch.object(loader.random, 'random', side_effect=[0.1, 0.8, 0.95]):
            created = loader.Command()._generate_validations(3, today)

        self.assertEqual(created, 3)
        new = list(Validation.objects.exclude(pk__in=before)
                   .select_related('evidence'))
        self.assertEqual(
            sorted(v.decision for v in new),
            ['Aprobada', 'Corrección solicitada', 'Rechazada'])
        status_for = {
            'Aprobada': Evidence.REVIEW_STATUS_APROBADA,
            'Rechazada': Evidence.REVIEW_STATUS_RECHAZADA,
            'Corrección solicitada': Evidence.REVIEW_STATUS_PENDIENTE,
        }
        for validation in new:
            with self.subTest(decision=validation.decision):
                self.assertEqual(
                    validation.result, validation.decision == 'Aprobada')
                self.assertTrue(validation.notes.strip())
                self.assertEqual(
                    validation.evidence.review_status,
                    status_for[validation.decision])


def _rows(model):
    manager = getattr(model, 'all_objects', model.objects)
    return list(manager.order_by('pk').values_list())


def snapshot():
    """Contenido completo (todas las columnas) de lo que toca el cargador,
    incluidos los hashes de contraseña y los eliminados lógicamente."""
    from organization.models import Delegation, Employee, Position
    from performance.models import CatalogItem
    models = (
        User, Group, User.groups.through, Delegation, Position, Employee,
        Period, CatalogItem, Meta, Activity, Evidence, Validation, Commitment,
    )
    return {model.__name__: _rows(model) for model in models}


class RerunTests(LoaderTestMixin, TestCase):
    """Parten de una base ya cargada (una sola carga para toda la clase)."""

    @classmethod
    def setUpTestData(cls):
        load()

    def test_a_second_run_changes_nothing(self):
        before = snapshot()
        load()
        self.assertEqual(snapshot(), before)

    def test_top_up_replaces_deleted_activities(self):
        # Solo se pueden eliminar actividades sin evidencias vivas.
        for activity in list(Activity.objects.filter(evidence_items__isnull=True)[:3]):
            activity.soft_delete()
        self.assertEqual(Activity.objects.count(), 27)

        load()

        # Solo se agrega lo que falta, y las nuevas quedan con meta coherente.
        self.assertEqual(Activity.objects.count(), 30)
        self.assertEqual(Evidence.objects.count(), 6)
        self.assertEqual(Activity.objects.filter(meta__isnull=True).count(), 2)

    def test_top_up_replaces_deleted_evidences_even_if_no_activity_is_missing(self):
        # generate_volume_data solo reparte evidencias entre las actividades
        # que crea en esa misma corrida; el cargador debe poder reponerlas
        # usando las ya existentes.
        # Se eliminan evidencias generadas: seed_sgr restaura las dos curadas
        # (EVID-001 y EVID-002) al empezar, y eso taparía lo que se prueba.
        generated = Evidence.objects.exclude(pk__in=('EVID-001', 'EVID-002'))
        for evidence in list(generated[:2]):
            evidence.soft_delete()  # su validación se elimina con ella
        self.assertEqual(Evidence.objects.count(), 4)
        activities_before = Activity.objects.count()

        load()

        self.assertEqual(Evidence.objects.count(), 6)
        self.assertEqual(Activity.objects.count(), activities_before)
        self.assertGreaterEqual(Validation.objects.count(), 1)

    def test_a_new_password_updates_and_an_altered_user_is_restored(self):
        admin = User.objects.get(username='api_admin')
        admin.is_staff = True
        admin.is_active = False
        admin.save()
        admin.groups.clear()
        User.objects.get(username='api_sinrol').groups.add(
            Group.objects.get(name=GROUP_API_ADMIN))

        new_password = 'Otra-Clave-2026!'
        load(password=new_password)

        for username, group in (('api_admin', GROUP_API_ADMIN),
                                ('api_operador', GROUP_API_OPERADOR),
                                ('api_sinrol', None)):
            with self.subTest(user=username):
                self.assertIsNotNone(
                    authenticate(username=username, password=new_password))
                self.assertIsNone(
                    authenticate(username=username, password=PASSWORD))
                user = User.objects.get(username=username)
                self.assertTrue(user.is_active)
                self.assertFalse(user.is_staff)
                self.assertEqual(
                    list(user.groups.values_list('name', flat=True)),
                    [group] if group else [])


class PasswordTests(LoaderTestMixin, TestCase):

    def test_there_is_no_default_password(self):
        with mock.patch.dict(os.environ):
            os.environ.pop(loader.PASSWORD_ENV_VAR, None)
            with self.assertRaisesMessage(CommandError, loader.PASSWORD_ENV_VAR):
                call_command('load_api_demo_data', stdout=StringIO())
        self.assertFalse(User.objects.exists())

    def test_a_short_password_is_rejected(self):
        with self.assertRaisesMessage(CommandError, 'al menos'):
            call_command('load_api_demo_data', password='corta', stdout=StringIO())
        self.assertFalse(User.objects.exists())

    def test_the_password_can_come_from_the_environment(self):
        with mock.patch.dict(os.environ, {loader.PASSWORD_ENV_VAR: PASSWORD}):
            call_command(
                'load_api_demo_data', stdout=StringIO(), stderr=StringIO(),
                **SMALL)
        self.assertIsNotNone(authenticate(username='api_admin', password=PASSWORD))

    def test_the_source_has_no_default_password(self):
        # La contraseña por defecto de seed_sgr no debe colarse en el cargador.
        # Se lee del propio seed_sgr para no repetir el valor aquí.
        seed_default = (
            SeedCommand().create_parser('manage.py', 'seed_sgr')
            .get_default('password'))
        self.assertTrue(seed_default)
        self.assertNotIn(seed_default, inspect.getsource(loader))


class RequirementsCheckTests(LoaderTestMixin, TestCase):

    def test_it_fails_when_a_model_is_empty_or_the_total_is_too_low(self):
        # seed_sgr no crea compromisos: con 0 el modelo queda vacío.
        with self.assertRaises(CommandError) as ctx:
            load(commitments=0, min_total=100000)
        message = str(ctx.exception)
        self.assertIn('modelos vacíos: Commitment', message)
        self.assertIn('no llega al mínimo', message)


class ReproducibilityTests(LoaderTestMixin, TestCase):

    @staticmethod
    def fingerprint():
        """Contenido de los datos generados, sin claves primarias ni nada que
        dependa del reloj (vencimientos) o de un UUID (nombres de archivo)."""
        return {
            'activities': list(Activity.objects.order_by('pk').values_list(
                'employee_id', 'period__start_date', 'date', 'activity_type',
                'service', 'attention__name', 'sub_attention',
                'request_description', 'action_taken', 'contact_name',
                'contact_phone', 'meta__item_name', 'meta__position__name')),
            'evidences': list(Evidence.objects.order_by('code').values_list(
                'code', 'activity__request_description', 'date', 'metadata',
                'review_status')),
            'commitments': list(Commitment.objects.order_by('pk').values_list(
                'delegation_id', 'responsible_id', 'origin', 'requester',
                'territory', 'support_area', 'status', 'observation')),
            'validations': list(Validation.objects.order_by('evidence_id')
                                .values_list('evidence_id', 'employee_id',
                                             'decision', 'date', 'result',
                                             'notes')),
        }

    def load_and_fingerprint(self, **overrides):
        """Carga sobre una base vacía y la deshace (savepoint) para poder
        repetir desde cero."""
        savepoint = transaction.savepoint()
        try:
            load(**overrides)
            return self.fingerprint()
        finally:
            transaction.savepoint_rollback(savepoint)

    def test_the_same_seed_gives_the_same_data_and_another_seed_does_not(self):
        first = self.load_and_fingerprint(seed=11)
        second = self.load_and_fingerprint(seed=11)
        other = self.load_and_fingerprint(seed=12)
        self.assertTrue(first['activities'])
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_the_random_state_is_left_as_it_was(self):
        # Una semilla fija no debe filtrarse al resto de la suite. Se parte de
        # un estado conocido y distinto del que deja una carga (otra semilla):
        # si no, un filtrado de un test anterior podría compararse "igual".
        original = (random.getstate(), loader.volume.fake.random.getstate())
        self.addCleanup(random.setstate, original[0])
        self.addCleanup(loader.volume.fake.random.setstate, original[1])
        random.seed(98765)
        loader.Faker.seed(98765)
        python_state = random.getstate()
        faker_state = loader.volume.fake.random.getstate()
        load()
        self.assertEqual(random.getstate(), python_state)
        self.assertEqual(loader.volume.fake.random.getstate(), faker_state)
