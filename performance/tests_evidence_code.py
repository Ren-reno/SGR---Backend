"""Pruebas del código de `Evidence` generado por el sistema (patch 19, Decisión 33).

Cubren las superficies que tocan el código:
- el modelo: formato, correlativo, conservar el código explícito, no reutilizar
  el de una evidencia eliminada, y las defensas de concurrencia (reintentar y
  no pisar la fila ajena);
- el campo: `editable=False`;
- el Admin: alta, edición, alta con `Validation` en línea y el inline de
  evidencias dentro de `Activity`;
- el seed, que sigue asignando sus códigos explícitos.

El formulario web y su mensaje de éxito se prueban en `tests_evidence_web.py`.
Las colisiones se simulan con `next_code` (SQLite serializa las escrituras, así
que dos peticiones reales no chocan en una prueba).

Correr con:  python manage.py test performance.tests_evidence_code
"""
from datetime import date
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.forms import modelform_factory
from django.test import Client, TestCase

from organization.models import Employee
from performance.models import Activity, Evidence, Validation
from performance.tests import (
    SEED_PASSWORD, MediaRootMixin, make_activity, make_world,
)


class EvidenceCodeTestCase(TestCase):
    """Datos mínimos y un atajo para crear evidencias sin escribir el código."""

    @classmethod
    def setUpTestData(cls):
        _delegation, employee, period, attention = make_world()
        cls.activity = make_activity(employee, period, attention)

    def unsaved(self, **kwargs):
        return Evidence(
            activity=self.activity, file='evidence/x.pdf',
            date=date(2026, 3, 1), **kwargs)

    def new_evidence(self, **kwargs):
        return Evidence.objects.create(
            activity=self.activity, file='evidence/x.pdf',
            date=date(2026, 3, 1), **kwargs)


class EvidenceCodeGenerationTests(EvidenceCodeTestCase):
    def test_the_first_code_is_evid_0001(self):
        self.assertEqual(Evidence.next_code(), 'EVID-0001')
        self.assertEqual(self.new_evidence().code, 'EVID-0001')

    def test_codes_are_consecutive(self):
        codes = [self.new_evidence().code for _ in range(3)]
        self.assertEqual(codes, ['EVID-0001', 'EVID-0002', 'EVID-0003'])

    def test_the_generated_code_is_the_primary_key_and_is_saved(self):
        evidence = self.new_evidence()
        self.assertEqual(evidence.pk, evidence.code)
        self.assertEqual(Evidence.objects.get(pk='EVID-0001'), evidence)

    def test_the_number_is_padded_to_four_digits_and_keeps_growing(self):
        self.new_evidence(code='EVID-9999')
        self.assertEqual(self.new_evidence().code, 'EVID-10000')
        self.assertEqual(self.new_evidence().code, 'EVID-10001')

    def test_it_continues_after_the_highest_number_even_with_gaps(self):
        self.new_evidence(code='EVID-0007')
        self.assertEqual(self.new_evidence().code, 'EVID-0008')

    def test_the_code_of_a_soft_deleted_evidence_is_not_reused(self):
        first = self.new_evidence()
        first.soft_delete()
        self.assertEqual(self.new_evidence().code, 'EVID-0002')

    def test_codes_without_the_form_are_ignored_and_break_nothing(self):
        # Filas anteriores a la Decisión 33 pueden traer cualquier texto.
        # "EVID-ABC" es el caso que rompería un CAST a entero en la base.
        for odd in ('A/B', 'FOTO-9', 'EVID-ABC', 'EVID-12X', 'EVID-', 'XEVID-5'):
            self.new_evidence(code=odd)
        self.assertEqual(self.new_evidence().code, 'EVID-0001')

    def test_the_prefix_is_matched_without_distinguishing_case(self):
        # Antes se podía escribir el código en minúscula.
        self.new_evidence(code='evid-0010')
        self.assertEqual(self.new_evidence().code, 'EVID-0011')

    def test_a_code_given_explicitly_is_kept(self):
        # El seed y los tests crean con código propio: `save()` no lo toca.
        evidence = self.new_evidence(code='EVID-001')
        self.assertEqual(evidence.code, 'EVID-001')
        self.assertEqual(Evidence.objects.get(pk='EVID-001'), evidence)
        self.assertEqual(self.new_evidence().code, 'EVID-0002')

    def test_saving_an_existing_evidence_never_changes_its_code(self):
        evidence = self.new_evidence()
        evidence.metadata = 'cambio'
        evidence.save()
        evidence.review_status = Evidence.REVIEW_STATUS_APROBADA
        evidence.save(update_fields=['review_status'])
        evidence.soft_delete()
        evidence.restore()
        self.assertEqual(evidence.code, 'EVID-0001')
        self.assertEqual(
            list(Evidence.all_objects.values_list('pk', flat=True)), ['EVID-0001'])

    def test_a_row_loaded_from_the_database_keeps_its_code_when_saved(self):
        self.new_evidence()
        evidence = Evidence.objects.get()
        evidence.metadata = 'x'
        evidence.save()
        self.assertEqual(
            list(Evidence.all_objects.values_list('pk', flat=True)), ['EVID-0001'])


class EvidenceCodeFieldTests(EvidenceCodeTestCase):
    def test_code_is_not_editable_and_is_still_the_primary_key(self):
        field = Evidence._meta.get_field('code')
        self.assertFalse(field.editable)
        self.assertTrue(field.primary_key)

    def test_no_model_form_offers_it(self):
        form_class = modelform_factory(Evidence, fields='__all__')
        self.assertNotIn('code', form_class.base_fields)

    def test_a_new_evidence_passes_full_clean_before_it_has_a_code(self):
        # El Admin y los formularios validan el modelo antes de guardar; el
        # código se asigna recién en save().
        evidence = self.unsaved()
        # `file='evidence/x.pdf'` (el helper) es solo un nombre que no existe
        # en disco, y desde la Fase 8 el validador abre el archivo para
        # comprobar su contenido. Se usa un PDF mínimo en memoria:
        # full_clean() no lo guarda, así que no escribe en /media/.
        evidence.file = SimpleUploadedFile(
            'x.pdf', b'%PDF-1.4 x', content_type='application/pdf')
        evidence.full_clean()


class EvidenceCodeCollisionTests(EvidenceCodeTestCase):
    """Dos peticiones pueden calcular el mismo número; la segunda choca con la
    clave primaria. Se simula haciendo que `next_code` devuelva primero un
    código ya ocupado. Se guarda con `.save()` y no con `objects.create()`
    porque `create()` ya fuerza el INSERT por su cuenta, y el formulario web y
    el Admin guardan con `.save()` a secas: ahí es donde hace falta el
    `force_insert` de `Evidence`."""

    def collide_once(self, taken_code):
        return mock.patch.object(
            Evidence, 'next_code', side_effect=[taken_code, 'EVID-0002'])

    def test_a_collision_is_retried_with_the_next_number(self):
        self.new_evidence(code='EVID-0001')
        evidence = self.unsaved()
        with self.collide_once('EVID-0001') as next_code:
            evidence.save()
        self.assertEqual(evidence.code, 'EVID-0002')
        self.assertEqual(next_code.call_count, 2)
        self.assertEqual(Evidence.objects.count(), 2)

    def test_a_collision_never_overwrites_the_row_that_took_the_number(self):
        # `code` es la clave primaria: sin `force_insert`, `save()` intenta
        # primero un UPDATE y pisaría en silencio la fila de la otra petición
        # en vez de fallar.
        taken = self.new_evidence(code='EVID-0001', metadata='original')
        evidence = self.unsaved(metadata='nueva')
        with self.collide_once('EVID-0001'):
            evidence.save()
        taken.refresh_from_db()
        self.assertEqual(taken.metadata, 'original')
        self.assertEqual(evidence.code, 'EVID-0002')

    def test_a_collision_with_a_soft_deleted_row_is_retried_too(self):
        # Entre que se calculó el número y se insertó, otra petición pudo
        # tomarlo y eliminarlo: sigue ocupado aunque no se vea en `objects`.
        self.new_evidence(code='EVID-0001').soft_delete()
        evidence = self.unsaved()
        with self.collide_once('EVID-0001'):
            evidence.save()
        self.assertEqual(evidence.code, 'EVID-0002')

    def test_a_collision_does_not_break_the_surrounding_transaction(self):
        # El Admin guarda dentro de un `atomic()`. Un INSERT fallido marca esa
        # transacción como inservible (Django lo hace en cualquier base, SQLite
        # incluida); por eso cada intento va en su propio savepoint.
        self.new_evidence(code='EVID-0001')
        evidence = self.unsaved()
        with transaction.atomic():
            with self.collide_once('EVID-0001'):
                evidence.save()
            # Si el fallo hubiera marcado la transacción, esta consulta
            # levantaría TransactionManagementError.
            self.assertEqual(Evidence.objects.count(), 2)

    def test_it_gives_up_after_the_maximum_attempts(self):
        self.new_evidence(code='EVID-0001')
        evidence = self.unsaved()
        with mock.patch.object(
            Evidence, 'next_code', return_value='EVID-0001',
        ) as next_code:
            with self.assertRaises(IntegrityError):
                evidence.save()
        self.assertEqual(next_code.call_count, Evidence.CODE_MAX_ATTEMPTS)
        # La instancia queda como "no guardada", sin un código que no es suyo.
        self.assertEqual(evidence.code, '')
        self.assertTrue(evidence._state.adding)
        self.assertEqual(Evidence.objects.count(), 1)

    def test_an_unrelated_integrity_error_is_not_retried(self):
        # `date` es obligatoria: con None la base rechaza el INSERT por NOT
        # NULL, no por el código. Reintentar no lo arreglaría.
        evidence = Evidence(
            activity=self.activity, file='evidence/x.pdf', date=None)
        with mock.patch.object(
            Evidence, 'next_code', wraps=Evidence.next_code,
        ) as next_code:
            with self.assertRaises(IntegrityError):
                evidence.save()
        self.assertEqual(next_code.call_count, 1)
        self.assertEqual(evidence.code, '')
        self.assertEqual(Evidence.objects.count(), 0)


class EvidenceCodeAdminTestCase(MediaRootMixin, TestCase):
    """Usan el seed (EVID-001 y EVID-002) para tener el Admin real."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_sgr', verbosity=0)

    def login(self):
        client = Client()
        self.assertTrue(client.login(username='admin_sgr', password=SEED_PASSWORD))
        return client

    @staticmethod
    def pdf(name='a.pdf'):
        return SimpleUploadedFile(name, b'%PDF-1.4 x', content_type='application/pdf')


class EvidenceCodeAdminTests(EvidenceCodeAdminTestCase):
    add_url = '/admin/performance/evidence/add/'
    change_url = '/admin/performance/evidence/EVID-001/change/'
    # Management form del inline de Validation (prefijo `validation`).
    no_inline = {
        'validation-TOTAL_FORMS': '0', 'validation-INITIAL_FORMS': '0',
        'validation-MIN_NUM_FORMS': '0', 'validation-MAX_NUM_FORMS': '1',
    }

    def add_payload(self, **overrides):
        data = {
            'activity': Activity.objects.order_by('pk').first().pk,
            'date': '2026-09-01', 'metadata': 'desde el Admin',
            'review_status': 'pendiente', 'file': self.pdf(), '_save': 'Save',
            **self.no_inline,
        }
        data.update(overrides)
        return data

    def test_the_add_form_has_no_code_input_and_shows_it_read_only(self):
        response = self.login().get(self.add_url)
        self.assertEqual(response.status_code, 200)
        adminform = response.context['adminform']
        self.assertNotIn('code', adminform.form.fields)
        self.assertEqual(list(adminform.readonly_fields), ['code'])
        self.assertNotContains(response, 'name="code"')
        self.assertContains(response, 'field-code')

    def test_the_code_is_the_first_row_of_the_form(self):
        response = self.login().get(self.change_url)
        fields = response.context['adminform'].fieldsets[0][1]['fields']
        self.assertEqual(fields[0], 'code')

    def test_the_change_page_shows_the_code_and_has_no_input_for_it(self):
        response = self.login().get(self.change_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="code"')
        self.assertContains(response, '<div class="readonly">EVID-001</div>')

    def test_the_admin_generates_the_code_on_add(self):
        # El seed trae EVID-001 y EVID-002.
        response = self.login().post(self.add_url, self.add_payload())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            sorted(Evidence.objects.values_list('pk', flat=True)),
            ['EVID-0003', 'EVID-001', 'EVID-002'])

    def test_a_code_sent_to_the_add_form_is_ignored(self):
        response = self.login().post(self.add_url, self.add_payload(
            code='EVID-001', metadata='intento de pisar'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Evidence.objects.get(pk='EVID-001').metadata, '')
        self.assertEqual(Evidence.objects.get(pk='EVID-0003').metadata, 'intento de pisar')

    def test_a_code_sent_to_the_change_form_is_ignored(self):
        # Si se leyera, cambiarlo haría que save() insertara una fila nueva y
        # dejara la original: dos evidencias en vez de una.
        before = Evidence.all_objects.count()
        original = Evidence.objects.get(pk='EVID-001')
        response = self.login().post(self.change_url, {
            'code': 'EVID-HACK', 'activity': original.activity_id,
            'date': str(original.date), 'metadata': 'editada',
            'review_status': original.review_status, '_save': 'Save',
            **self.no_inline,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Evidence.all_objects.count(), before)
        self.assertFalse(Evidence.all_objects.filter(pk='EVID-HACK').exists())
        self.assertEqual(Evidence.objects.get(pk='EVID-001').metadata, 'editada')

    def test_the_admin_adds_an_evidence_with_its_validation_on_the_same_screen(self):
        # El inline de Validation se guarda contra la clave recién generada.
        verifier = Employee.objects.get(user__username='verificador_demo')
        response = self.login().post(self.add_url, self.add_payload(**{
            'validation-TOTAL_FORMS': '1',
            'validation-0-employee': verifier.pk,
            'validation-0-decision': 'Aprobada',
            'validation-0-date': '2026-09-02',
            'validation-0-notes': 'conforme',
            'validation-0-result': 'on',
            'validation-0-version': '1',
        }))
        self.assertEqual(response.status_code, 302)
        validation = Validation.objects.get(notes='conforme')
        self.assertEqual(validation.evidence_id, 'EVID-0003')


class EvidenceCodeActivityInlineTests(EvidenceCodeAdminTestCase):
    """El inline de evidencias dentro de `ActivityAdmin`. Con el código
    `editable=False`, Django agrega la clave primaria como campo oculto para
    distinguir las filas."""

    def setUp(self):
        self.activity = Activity.objects.order_by('pk').first()
        self.existing = Evidence.objects.get(activity=self.activity)
        self.url = f'/admin/performance/activity/{self.activity.pk}/change/'

    def payload(self, new_row):
        """POST del formulario de la actividad con su evidencia existente y
        una fila nueva en el inline (`evidence_items`)."""
        form = self.client.get(self.url).context['adminform'].form
        data = {
            name: value for name, value in form.initial.items()
            if name in form.fields and value is not None
        }
        data.update({
            'evidence_items-TOTAL_FORMS': '2',
            'evidence_items-INITIAL_FORMS': '1',
            'evidence_items-MIN_NUM_FORMS': '0',
            'evidence_items-MAX_NUM_FORMS': '1000',
            'evidence_items-0-code': self.existing.pk,
            'evidence_items-0-activity': self.activity.pk,
            'evidence_items-0-date': str(self.existing.date),
            'evidence_items-0-metadata': '',
            'evidence_items-0-review_status': self.existing.review_status,
            'evidence_items-1-activity': self.activity.pk,
            'evidence_items-1-date': '2026-09-03',
            'evidence_items-1-metadata': 'desde el inline',
            'evidence_items-1-review_status': 'pendiente',
            'evidence_items-1-file': SimpleUploadedFile(
                'n.pdf', b'%PDF-1.4 n', content_type='application/pdf'),
            '_save': 'Save',
        })
        data.update(new_row)
        return data

    def test_a_new_inline_row_gets_a_generated_code(self):
        self.client = self.login()
        response = self.client.post(self.url, self.payload({'evidence_items-1-code': ''}))
        self.assertEqual(response.status_code, 302)
        created = Evidence.objects.get(metadata='desde el inline')
        self.assertEqual(created.code, 'EVID-0003')
        self.assertEqual(created.activity, self.activity)

    def test_a_code_sent_for_a_new_row_does_not_touch_another_evidence(self):
        # El campo oculto de una fila nueva apunta a la evidencia de OTRA
        # actividad: no debe modificarla ni reasignarla; se crea una nueva.
        self.client = self.login()
        other = Evidence.objects.exclude(activity=self.activity).get()
        response = self.client.post(
            self.url, self.payload({'evidence_items-1-code': other.pk}))
        self.assertEqual(response.status_code, 302)
        other.refresh_from_db()
        self.assertEqual(other.metadata, '')
        self.assertNotEqual(other.activity, self.activity)
        self.assertEqual(Evidence.objects.get(metadata='desde el inline').code, 'EVID-0003')


class EvidenceCodeSeedTests(MediaRootMixin, TestCase):
    def test_the_seed_keeps_its_explicit_codes_and_can_run_twice(self):
        call_command('seed_sgr', verbosity=0)
        call_command('seed_sgr', verbosity=0)
        self.assertEqual(
            sorted(Evidence.all_objects.values_list('pk', flat=True)),
            ['EVID-001', 'EVID-002'])

    def test_a_generated_code_continues_after_the_seed_ones(self):
        call_command('seed_sgr', verbosity=0)
        activity = Activity.objects.order_by('pk').first()
        evidence = Evidence.objects.create(
            activity=activity, file='evidence/x.pdf', date=activity.date)
        self.assertEqual(evidence.code, 'EVID-0003')
