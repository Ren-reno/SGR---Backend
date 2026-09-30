"""Pruebas de `Evidence.review_status` como conjunto cerrado (patch 16, Decisión 30).

Cubren las cuatro superficies que tocan el campo:
- el modelo (choices, default, etiqueta visible);
- la migración de datos que normaliza las grafías antiguas;
- el seed y la acción masiva del Admin (los dos únicos que lo escriben);
- las pantallas que lo muestran (Admin y CRUD web).

Corren sobre el seed real, igual que las pruebas del Admin de `tests.py`.
Correr con:  python manage.py test performance.tests_review_status
"""
import importlib
import re

from django import forms
from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from performance.models import Evidence
from performance.tests import SEED_PASSWORD, MediaRootMixin

migration_0008 = importlib.import_module(
    'performance.migrations.0008_evidence_review_status_choices')


class ReviewStatusModelTests(TestCase):
    field = Evidence._meta.get_field('review_status')

    def test_the_closed_set_is_pendiente_aprobada_rechazada_in_lowercase(self):
        self.assertEqual(
            [value for value, _label in self.field.choices],
            ['pendiente', 'aprobada', 'rechazada'])

    def test_the_default_is_pendiente(self):
        self.assertEqual(self.field.default, Evidence.REVIEW_STATUS_PENDIENTE)
        self.assertEqual(Evidence().review_status, 'pendiente')

    def test_labels_are_capitalized(self):
        self.assertEqual(
            dict(self.field.choices),
            {'pendiente': 'Pendiente', 'aprobada': 'Aprobada',
             'rechazada': 'Rechazada'})
        self.assertEqual(
            Evidence(review_status='aprobada').get_review_status_display(),
            'Aprobada')

    def test_valid_values_pass_validation(self):
        for value in ('pendiente', 'aprobada', 'rechazada'):
            with self.subTest(value=value):
                self.assertEqual(self.field.clean(value, None), value)

    def test_the_old_capitalized_spellings_and_free_text_are_rejected(self):
        for value in ('Pendiente', 'Aprobada', 'APROBADA', 'en revisión', ''):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    self.field.clean(value, None)

    def test_it_still_fits_the_column(self):
        # El campo sigue en max_length=30: ninguna etiqueta ni valor se acerca.
        self.assertEqual(self.field.max_length, 30)
        self.assertTrue(all(len(v) <= 30 for v, _ in self.field.choices))


class NormalizeReviewStatusMigrationTests(MediaRootMixin, TestCase):
    """Ejecuta la función de datos de la migración 0008 sobre filas reales."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_sgr', verbosity=0)
        base = Evidence.objects.get(code='EVID-001')
        cls.codes = {}
        for code, value in [
            ('EVID-OLD-P', 'Pendiente'),
            ('EVID-OLD-A', 'Aprobada'),
            ('EVID-UP-A', 'APROBADA'),
            ('EVID-OLD-R', 'Rechazada'),
            ('EVID-OK-R', 'rechazada'),
            ('EVID-DEL', 'Aprobada'),
            ('EVID-ODD', 'otra cosa'),
        ]:
            Evidence.objects.create(
                code=code, activity=base.activity, file=base.file.name,
                date=base.date)
            cls.codes[code] = value
        # `update()` no valida: es la forma de dejar en la base lo que las
        # versiones anteriores escribían a mano.
        for code, value in cls.codes.items():
            Evidence.all_objects.filter(pk=code).update(review_status=value)
        Evidence.objects.get(code='EVID-DEL').soft_delete()

    def status_of(self, code):
        return Evidence.all_objects.get(pk=code).review_status

    def run_migration(self):
        migration_0008.normalize_review_status(django_apps, None)

    def test_every_capitalization_variant_becomes_lowercase(self):
        self.run_migration()
        self.assertEqual(self.status_of('EVID-OLD-P'), 'pendiente')
        self.assertEqual(self.status_of('EVID-OLD-A'), 'aprobada')
        self.assertEqual(self.status_of('EVID-UP-A'), 'aprobada')
        self.assertEqual(self.status_of('EVID-OLD-R'), 'rechazada')

    def test_already_normalized_rows_are_left_as_they_are(self):
        self.run_migration()
        self.assertEqual(self.status_of('EVID-OK-R'), 'rechazada')

    def test_soft_deleted_rows_are_normalized_too(self):
        self.assertIsNotNone(Evidence.all_objects.get(pk='EVID-DEL').deleted_at)
        self.run_migration()
        self.assertEqual(self.status_of('EVID-DEL'), 'aprobada')

    def test_an_unknown_value_is_not_guessed(self):
        self.run_migration()
        self.assertEqual(self.status_of('EVID-ODD'), 'otra cosa')

    def test_running_it_twice_changes_nothing_more(self):
        self.run_migration()
        first = dict(Evidence.all_objects.values_list('pk', 'review_status'))
        self.run_migration()
        self.assertEqual(
            dict(Evidence.all_objects.values_list('pk', 'review_status')), first)

    def test_the_migration_has_a_reverse_so_it_can_be_unapplied(self):
        operations = migration_0008.Migration.operations
        run_python = [op for op in operations
                      if op.__class__.__name__ == 'RunPython']
        self.assertEqual(len(run_python), 1)
        self.assertTrue(run_python[0].reversible)


class ReviewStatusSeedAndAdminTests(MediaRootMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_sgr', verbosity=0)

    def login(self, username='admin_sgr'):
        client = Client()
        self.assertTrue(client.login(username=username, password=SEED_PASSWORD))
        return client

    def test_the_seed_saves_the_lowercase_value(self):
        statuses = set(Evidence.all_objects.values_list('review_status', flat=True))
        self.assertEqual(statuses, {'pendiente'})

    def test_bulk_approve_saves_the_lowercase_value(self):
        # EVID-001 es la evidencia del seed sin validación.
        self.assertEqual(Evidence.objects.get(code='EVID-001').review_status, 'pendiente')
        response = self.login().post('/admin/performance/evidence/', {
            'action': 'approve_evidence_in_bulk',
            '_selected_action': ['EVID-001'],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Evidence.objects.get(code='EVID-001').review_status, 'aprobada')

    def test_bulk_approve_leaves_excluded_evidence_untouched(self):
        # EVID-002 ya tiene validación: la acción la excluye (Decisión 9-bis).
        self.login().post('/admin/performance/evidence/', {
            'action': 'approve_evidence_in_bulk',
            '_selected_action': ['EVID-002'],
        }, follow=True)
        self.assertEqual(
            Evidence.objects.get(code='EVID-002').review_status, 'pendiente')

    def test_the_admin_field_is_a_dropdown_with_the_three_values(self):
        response = self.login().get(
            '/admin/performance/evidence/EVID-001/change/')
        self.assertEqual(response.status_code, 200)
        field = response.context['adminform'].form.fields['review_status']
        self.assertIsInstance(field, forms.ChoiceField)
        self.assertEqual(
            [value for value, _ in field.choices],
            ['pendiente', 'aprobada', 'rechazada'])

    def test_the_admin_field_rejects_the_old_capitalized_value(self):
        response = self.login().get(
            '/admin/performance/evidence/EVID-001/change/')
        field = response.context['adminform'].form.fields['review_status']
        self.assertEqual(field.clean('aprobada'), 'aprobada')
        with self.assertRaises(ValidationError):
            field.clean('Aprobada')

    def test_the_admin_filter_offers_the_three_labels(self):
        response = self.login().get('/admin/performance/evidence/')
        self.assertEqual(response.status_code, 200)
        spec = next(s for s in response.context['cl'].filter_specs
                    if s.field_path == 'review_status')
        labels = [choice['display'] for choice in spec.choices(response.context['cl'])]
        self.assertEqual(labels, ['All', 'Pendiente', 'Aprobada', 'Rechazada'])


class ReviewStatusWebTests(MediaRootMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_sgr', verbosity=0)
        base = Evidence.objects.get(code='EVID-001')
        Evidence.objects.create(
            code='EVID-003', activity=base.activity, file=base.file.name,
            date=base.date)
        Evidence.objects.filter(pk='EVID-001').update(review_status='aprobada')
        Evidence.objects.filter(pk='EVID-002').update(review_status='rechazada')

    def setUp(self):
        self.client = Client()
        self.assertTrue(
            self.client.login(username='admin_sgr', password=SEED_PASSWORD))

    def badges(self):
        html = self.client.get(reverse('performance:evidence_list')).content.decode()
        return re.findall(r'<span class="badge (badge-[a-z]+)">([^<]*)</span>', html)

    def test_the_list_shows_the_label_and_not_the_stored_value(self):
        labels = sorted(label for _cls, label in self.badges())
        self.assertEqual(labels, ['Aprobada', 'Pendiente', 'Rechazada'])

    def test_each_status_keeps_its_own_badge_color(self):
        by_label = {label: css for css, label in self.badges()}
        self.assertEqual(by_label['Aprobada'], 'badge-ok')
        self.assertEqual(by_label['Rechazada'], 'badge-err')
        self.assertEqual(by_label['Pendiente'], 'badge-warn')

    def test_a_value_outside_the_set_gets_the_neutral_badge(self):
        # Una fila que la migración no pudo normalizar no rompe el listado.
        Evidence.objects.filter(pk='EVID-003').update(review_status='otra cosa')
        by_label = {label: css for css, label in self.badges()}
        self.assertEqual(by_label['otra cosa'], 'badge-neutral')

    def test_the_edit_form_shows_the_label_as_read_only_data(self):
        response = self.client.get(
            reverse('performance:evidence_update', args=['EVID-001']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<strong>Aprobada</strong>', html=True)
        self.assertNotIn('review_status', response.context['form'].fields)
