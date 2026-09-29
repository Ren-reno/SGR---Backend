"""Pruebas del borrado lógico (Fase 3, Decisión 20).

Tres bloques:
- SoftDeleteModelTests: el patrón en sí, sobre las 4 entidades.
- SoftDeleteAdminTests: que el Admin no borre nada de verdad y respete
  permisos y Delegación.
- SoftDeleteSeedTests: que el seed no se rompa contra filas eliminadas.

Correr con:  python manage.py test performance
"""
import shutil
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models import ProtectedError
from django.test import Client, TestCase, override_settings

from organization.models import Delegation, Employee, Position
from performance.models import (
    Activity, CatalogItem, Commitment, Evidence, Period, Validation,
)

User = get_user_model()

SEED_PASSWORD = 'sgr-demo-2026'
SOFT_MODELS = (Activity, Evidence, Validation, Commitment)


def make_world():
    """Datos mínimos para las 4 entidades, sin depender del seed."""
    delegation = Delegation.objects.create(id='D-T', name='Delegación T', scope='x')
    position = Position.objects.create(name='Analista')
    user = User.objects.create_user('emp_t', password='x')
    employee = Employee.objects.create(
        institutional_id='E-T', user=user, delegation=delegation,
        position=position, name='Emp T',
    )
    period = Period.objects.create(
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        computable_days=200, status='open',
        amber_threshold=70, collective_threshold=80,
    )
    # La migración 0003 ya siembra los 6 valores fijos de 'attention'.
    attention, _ = CatalogItem.objects.get_or_create(category='attention', name='Otros')
    return delegation, employee, period, attention


def make_activity(employee, period, attention, description='act'):
    return Activity.objects.create(
        employee=employee, period=period, attention=attention,
        activity_type='t', service='s', sub_attention='sa',
        date=date(2026, 3, 1), request_description=description,
        action_taken='a', status='Pendiente',
    )


def make_evidence(activity, code='EV-T'):
    return Evidence.objects.create(
        code=code, activity=activity, file='evidence/x.pdf', date=date(2026, 3, 1),
    )


def make_validation(evidence, employee):
    return Validation.objects.create(
        evidence=evidence, employee=employee, decision='Aprobada',
        date=date(2026, 3, 2), result=True,
    )


def make_commitment(delegation, employee, origin='origen'):
    return Commitment.objects.create(
        delegation=delegation, responsible=employee, origin=origin,
        requester='req', territory='t', due_date=date(2026, 6, 1),
    )


class SoftDeleteModelTests(TestCase):
    def setUp(self):
        self.delegation, self.employee, self.period, self.attention = make_world()
        self.activity = make_activity(self.employee, self.period, self.attention)
        self.evidence = make_evidence(self.activity)
        self.validation = make_validation(self.evidence, self.employee)
        self.commitment = make_commitment(self.delegation, self.employee)

    def _leaf(self, model):
        """Una instancia por modelo. Las que tienen hijos se prueban aparte."""
        # Lazy (lambdas): un dict con valores directos crearía las 4 a la vez.
        return {
            Activity: lambda: make_activity(
                self.employee, self.period, self.attention, 'hoja'),
            Evidence: lambda: make_evidence(
                make_activity(self.employee, self.period, self.attention, 'h2'), 'EV-H'),
            Validation: lambda: self.validation,
            Commitment: lambda: self.commitment,
        }[model]()

    def test_soft_delete_hides_the_row_but_keeps_it(self):
        for model in SOFT_MODELS:
            with self.subTest(model=model.__name__):
                obj = self._leaf(model)
                obj.soft_delete()
                self.assertFalse(model.objects.filter(pk=obj.pk).exists())
                kept = model.all_objects.get(pk=obj.pk)
                self.assertIsNotNone(kept.deleted_at)

    def test_delete_and_queryset_delete_are_logical(self):
        for model in SOFT_MODELS:
            with self.subTest(model=model.__name__):
                obj = self._leaf(model)
                obj.delete()
                self.assertTrue(model.all_objects.filter(pk=obj.pk).exists())
        extra = make_commitment(self.delegation, self.employee, 'otro')
        Commitment.objects.filter(pk=extra.pk).delete()
        self.assertFalse(Commitment.objects.filter(pk=extra.pk).exists())
        self.assertTrue(Commitment.all_objects.filter(pk=extra.pk).exists())

    def test_hard_delete_is_the_only_physical_delete(self):
        self.commitment.hard_delete()
        self.assertFalse(Commitment.all_objects.filter(pk=self.commitment.pk).exists())
        other = make_commitment(self.delegation, self.employee, 'otro')
        Commitment.all_objects.filter(pk=other.pk).hard_delete()
        self.assertFalse(Commitment.all_objects.filter(pk=other.pk).exists())

    def test_restore_shows_the_row_again(self):
        self.commitment.soft_delete()
        self.commitment.restore()
        self.assertTrue(Commitment.objects.filter(pk=self.commitment.pk).exists())

    def test_soft_delete_twice_is_harmless(self):
        self.assertTrue(self.commitment.soft_delete())
        self.assertFalse(self.commitment.soft_delete())

    def test_activity_with_live_evidence_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.activity.soft_delete()
        self.assertTrue(Activity.objects.filter(pk=self.activity.pk).exists())
        # Igual que hoy con PROTECT: cuando ya no tiene evidencias vivas, sí.
        self.evidence.soft_delete()
        self.activity.soft_delete()
        self.assertFalse(Activity.objects.filter(pk=self.activity.pk).exists())

    def test_bulk_delete_is_all_or_nothing(self):
        free = make_activity(self.employee, self.period, self.attention, 'libre')
        with self.assertRaises(ProtectedError):
            Activity.objects.filter(pk__in=[free.pk, self.activity.pk]).delete()
        self.assertTrue(Activity.objects.filter(pk=free.pk).exists())

    def test_evidence_delete_also_hides_its_validation(self):
        self.evidence.soft_delete()
        self.assertFalse(Validation.objects.filter(pk=self.validation.pk).exists())
        self.assertTrue(Validation.all_objects.filter(pk=self.validation.pk).exists())

    def test_related_managers_hide_deleted_children(self):
        self.evidence.soft_delete()
        self.assertEqual(self.activity.evidence_items.count(), 0)

    def test_old_row_can_still_read_its_deleted_parent(self):
        self.evidence.soft_delete()
        self.activity.soft_delete()
        old = Evidence.all_objects.get(pk=self.evidence.pk)
        self.assertEqual(old.activity.pk, self.activity.pk)  # no lanza excepción

    def test_dropdown_and_forms_do_not_offer_deleted_rows(self):
        from django import forms

        class ValidationForm(forms.ModelForm):
            class Meta:
                model = Validation
                fields = ['evidence']

        free = make_evidence(
            make_activity(self.employee, self.period, self.attention, 'otra'), 'EV-F')
        self.evidence.soft_delete()  # esconde EV-T y su validación
        offered = set(ValidationForm().fields['evidence'].queryset.values_list('pk', flat=True))
        self.assertIn(free.pk, offered)
        self.assertNotIn(self.evidence.pk, offered)
        form = ValidationForm(data={'evidence': self.evidence.pk})
        self.assertFalse(form.is_valid())

    def test_unique_values_of_deleted_rows_give_a_form_error_not_a_500(self):
        # Validation.evidence (OneToOne): la fila eliminada sigue ocupando el lugar.
        self.validation.soft_delete()
        clone = Validation(
            evidence=self.evidence, employee=self.employee, decision='Aprobada',
            date=date(2026, 3, 3), result=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            clone.validate_unique()
        self.assertIn('evidence', ctx.exception.message_dict)
        # Evidence.code (PK natural): lo mismo.
        self.evidence.soft_delete()
        dup = Evidence(code=self.evidence.code, activity=self.activity,
                       file='evidence/y.pdf', date=date(2026, 3, 1))
        with self.assertRaises(ValidationError) as ctx:
            dup.validate_unique()
        self.assertIn('code', ctx.exception.message_dict)

    def test_editing_a_live_row_still_passes_unique_validation(self):
        self.validation.validate_unique()
        self.evidence.validate_unique()


class MediaRootMixin:
    """Los tests que corren el seed suben PDFs; se guardan en una carpeta
    temporal para no ensuciar /media/ del proyecto."""

    @classmethod
    def setUpClass(cls):
        cls._media = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._media)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)


class SoftDeleteAdminTests(MediaRootMixin, TestCase):
    """Usan el seed para tener los grupos y permisos reales del proyecto."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_sgr', verbosity=0)
        cls.centro = Delegation.objects.get(id='DEL-001')
        cls.norte = Delegation.objects.get(id='DEL-002')
        cls.emp_norte = Employee.objects.get(user__username='funcionario_demo')
        cls.emp_centro = Employee.objects.get(user__username='verificador_demo')
        cls.c_norte = make_commitment(cls.norte, cls.emp_norte, 'NORTE-1')
        cls.c_centro = make_commitment(cls.centro, cls.emp_centro, 'CENTRO-1')

    def login(self, username):
        client = Client()
        self.assertTrue(client.login(username=username, password=SEED_PASSWORD))
        return client

    def delete_url(self, model, pk):
        return f'/admin/performance/{model}/{pk}/delete/'

    def test_admin_delete_of_commitment_is_logical(self):
        client = self.login('admin_sgr')
        response = client.post(self.delete_url('commitment', self.c_norte.pk), {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        row = Commitment.all_objects.get(pk=self.c_norte.pk)  # la fila sigue
        self.assertIsNotNone(row.deleted_at)
        # Se mira la tabla (result_list), no todo el HTML: el mensaje de éxito
        # "was deleted successfully" repite el nombre del registro borrado.
        shown = [c.origin for c in client.get('/admin/performance/commitment/').context['cl'].result_list]
        self.assertEqual(shown, ['CENTRO-1'])

    def test_bulk_delete_selected_action_is_logical(self):
        client = self.login('admin_sgr')
        client.post('/admin/performance/commitment/', {
            'action': 'delete_selected', 'post': 'yes',
            '_selected_action': [self.c_norte.pk, self.c_centro.pk],
        })
        for pk in (self.c_norte.pk, self.c_centro.pk):
            self.assertIsNotNone(Commitment.all_objects.get(pk=pk).deleted_at)

    def test_only_administrator_can_delete_commitment(self):
        client = self.login('funcionario_demo')
        client.post(self.delete_url('commitment', self.c_norte.pk), {'post': 'yes'})
        self.assertIsNone(Commitment.all_objects.get(pk=self.c_norte.pk).deleted_at)
        client = self.login('verificador_demo')
        client.post(self.delete_url('commitment', self.c_centro.pk), {'post': 'yes'})
        self.assertIsNone(Commitment.all_objects.get(pk=self.c_centro.pk).deleted_at)

    def test_administrator_has_no_delegation_restriction_even_with_employee(self):
        # Decisión 6 (previa a esta fase): Administrador nunca tiene
        # restricción de Delegación, tenga o no Employee asociado. No es un
        # caso a aislar por scoping: es el comportamiento correcto. Sirve de
        # control para no repetir el error de una versión anterior de esta
        # prueba, que esperaba (equivocadamente) lo contrario.
        from django.contrib.auth.models import Group
        position = Employee.objects.get(user__username='funcionario_demo').position
        user = User.objects.create_user('admin_norte', password='x', is_staff=True)
        user.groups.add(Group.objects.get(name='Administrador'))
        Employee.objects.create(institutional_id='ADM-N', user=user, delegation=self.norte,
                                position=position, name='Admin Norte')
        client = Client()
        self.assertTrue(client.login(username='admin_norte', password='x'))
        client.post(self.delete_url('commitment', self.c_centro.pk), {'post': 'yes'})
        self.assertIsNotNone(Commitment.all_objects.get(pk=self.c_centro.pk).deleted_at)

    def test_delegation_scoping_of_commitment_delete_is_enforced_if_ever_granted(self):
        # A través del Admin (HTTP) esta rama de has_delete_permission es
        # inalcanzable: CommitmentAdmin.get_queryset() ya filtra por
        # Delegación (patch 5), así que get_object() para un Commitment
        # ajeno devuelve None ANTES de que has_delete_permission se llame
        # con un obj real -- probarlo por HTTP no ejercitaría el scoping,
        # solo el filtro del queryset (que es una prueba distinta, ya
        # cubierta por test_changelists_hide_deleted_rows_for_all_four_models).
        # Con el seed actual nadie combina delete_commitment con una
        # Delegación restringida (Administrador es el único con ese
        # permiso, y nunca está scopeado -- Decisión 6), así que esta rama
        # es puramente defensiva hoy: protege una vista futura de Fase 6
        # que llame a has_delete_permission(request, obj) con un obj
        # obtenido sin pasar por get_queryset. Se prueba llamando al
        # método directamente, que es la única forma de ejercitarla.
        from performance.admin import CommitmentAdmin
        from django.contrib.admin.sites import site
        from django.test import RequestFactory
        from django.contrib.auth.models import Permission

        position = Employee.objects.get(user__username='funcionario_demo').position
        user = User.objects.create_user('con_permiso_norte', password='x', is_staff=True)
        user.user_permissions.add(Permission.objects.get(
            content_type__app_label='performance', codename='delete_commitment'))
        Employee.objects.create(institutional_id='PERM-N', user=user, delegation=self.norte,
                                position=position, name='Con Permiso Norte')
        request = RequestFactory().get('/')
        request.user = user
        model_admin = CommitmentAdmin(Commitment, site)
        self.assertFalse(model_admin.has_delete_permission(request, self.c_centro),
                         "el scoping por Delegación no bloqueó el Commitment ajeno")
        self.assertTrue(model_admin.has_delete_permission(request, self.c_norte),
                        "el scoping por Delegación bloqueó también el propio")

    def test_verifier_scoped_to_own_delegation_cannot_delete_foreign_validation(self):
        # Igual que en CommitmentAdmin (ver el comentario largo en
        # test_delegation_scoping_of_commitment_delete_is_enforced_if_ever_granted):
        # ValidationAdmin.get_queryset() también filtra por Delegación, así
        # que por HTTP un Verificador de Norte pidiendo una Validation de
        # Centro recibe obj=None antes de llegar al scoping dentro de
        # has_delete_permission -- probarlo por HTTP no detectaba el
        # sabotaje 7. Se llama al método directamente, con un obj real.
        #
        # La única Validation del seed (para EVID-002) es de Norte, no de
        # Centro -- no sirve como caso "ajeno" para un Verificador de
        # Norte. Se construye una propia, de Centro, con el helper make_*.
        from performance.admin import ValidationAdmin
        from django.contrib.admin.sites import site
        from django.contrib.auth.models import Group, Permission
        from django.test import RequestFactory

        centro_activity = make_activity(self.emp_centro, Period.objects.first(),
                                        CatalogItem.objects.filter(category='attention').first(),
                                        'para validar (centro)')
        centro_evidence = make_evidence(centro_activity, 'EV-CENTRO-T')
        foreign_validation = make_validation(centro_evidence, self.emp_centro)
        self.assertEqual(foreign_validation.evidence.activity.employee.delegation_id, self.centro.pk)

        position = Employee.objects.get(user__username='funcionario_demo').position
        user = User.objects.create_user('verif_norte', password='x', is_staff=True)
        user.groups.add(Group.objects.get(name='Verificador'))
        # delete_validation se otorga aparte (no lo tiene el grupo
        # Verificador, solo Administrador -- Decisión 20): sin esto,
        # super().has_delete_permission() ya devuelve False por el permiso
        # de modelo, y nunca se llega a evaluar el scoping por rol+Delegación
        # que esta prueba quiere aislar.
        user.user_permissions.add(Permission.objects.get(
            content_type__app_label='performance', codename='delete_validation'))
        Employee.objects.create(institutional_id='VER-N', user=user, delegation=self.norte,
                                position=position, name='Verif Norte')
        request = RequestFactory().get('/')
        request.user = user
        model_admin = ValidationAdmin(Validation, site)
        self.assertFalse(model_admin.has_delete_permission(request, foreign_validation),
                         "el scoping por Delegación no bloqueó la Validation ajena")
        self.assertFalse(Validation.all_objects.get(pk=foreign_validation.pk).deleted_at)

    def test_validation_delete_is_logical_and_administrator_only(self):
        validation = Validation.objects.get()
        url = self.delete_url('validation', validation.pk)
        self.login('verificador_demo').post(url, {'post': 'yes'})
        self.assertIsNone(Validation.all_objects.get(pk=validation.pk).deleted_at)
        self.login('funcionario_demo').post(url, {'post': 'yes'})
        self.assertIsNone(Validation.all_objects.get(pk=validation.pk).deleted_at)
        response = self.login('admin_sgr').post(url, {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(Validation.all_objects.get(pk=validation.pk).deleted_at)

    def test_admin_delete_of_evidence_hides_it_and_its_validation(self):
        evidence = Evidence.objects.get(code='EVID-002')
        response = self.login('admin_sgr').post(
            self.delete_url('evidence', evidence.pk), {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(Evidence.all_objects.get(pk='EVID-002').deleted_at)
        self.assertEqual(Validation.objects.count(), 0)
        self.assertEqual(Validation.all_objects.count(), 1)

    def test_changelists_hide_deleted_rows_for_all_four_models(self):
        Commitment.objects.filter(pk=self.c_norte.pk).delete()
        Evidence.objects.get(code='EVID-002').soft_delete()
        Evidence.objects.get(code='EVID-001').soft_delete()
        Activity.objects.all().delete()
        client = self.login('admin_sgr')
        for model in ('activity', 'evidence', 'validation', 'commitment'):
            with self.subTest(model=model):
                response = client.get(f'/admin/performance/{model}/')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['cl'].result_count,
                                 1 if model == 'commitment' else 0)

    def test_deleted_row_is_not_reachable_by_direct_url(self):
        Commitment.objects.filter(pk=self.c_norte.pk).delete()
        response = self.login('admin_sgr').get(
            f'/admin/performance/commitment/{self.c_norte.pk}/change/')
        self.assertIn(response.status_code, (302, 404))

    def test_bulk_approve_reports_a_deleted_validation_instead_of_crashing(self):
        Validation.objects.get().soft_delete()  # EVID-002 queda con su validación escondida
        client = self.login('admin_sgr')
        response = client.post('/admin/performance/evidence/', {
            'action': 'approve_evidence_in_bulk',
            '_selected_action': ['EVID-002'],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        text = ' '.join(str(m) for m in response.context['messages'])
        self.assertIn('validación fue eliminada', text)
        self.assertEqual(Validation.all_objects.count(), 1)

    def test_evidence_page_with_deleted_validation_gives_form_error_not_500(self):
        Validation.objects.get().soft_delete()
        client = self.login('admin_sgr')
        url = '/admin/performance/evidence/EVID-002/change/'
        page = client.get(url)
        self.assertEqual(page.status_code, 200)
        formset = next(fs for fs in page.context['inline_admin_formsets']
                       if fs.formset.model is Validation).formset
        prefix = formset.prefix
        data = {
            'activity': Evidence.objects.get(code='EVID-002').activity_id,
            'date': '2026-08-12', 'metadata': '', 'review_status': 'Pendiente',
            f'{prefix}-TOTAL_FORMS': '1', f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1',
            f'{prefix}-0-employee': Employee.objects.get(user__username='verificador_demo').pk,
            f'{prefix}-0-decision': 'Aprobada', f'{prefix}-0-date': '2026-08-21',
            f'{prefix}-0-notes': '', f'{prefix}-0-result': 'on', f'{prefix}-0-version': '1',
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 200)  # vuelve al formulario con el error
        self.assertEqual(Validation.all_objects.count(), 1)


class SoftDeleteSeedTests(MediaRootMixin, TestCase):
    def test_seed_grants_delete_of_validation_and_commitment_only_to_administrator(self):
        call_command('seed_sgr', verbosity=0)

        def codenames(group):
            return set(Group.objects.get(name=group).permissions.values_list('codename', flat=True))

        self.assertLessEqual({'delete_validation', 'delete_commitment'}, codenames('Administrador'))
        for group in ('Funcionario', 'Verificador'):
            self.assertFalse({p for p in codenames(group) if p.startswith('delete_')})

    def test_seed_restores_deleted_demo_data_instead_of_crashing(self):
        call_command('seed_sgr', verbosity=0)
        before = (Activity.all_objects.count(), Evidence.all_objects.count(),
                  Validation.all_objects.count())
        Evidence.objects.get(code='EVID-002').soft_delete()  # arrastra su validación
        call_command('seed_sgr', verbosity=0)  # antes: IntegrityError
        after = (Activity.all_objects.count(), Evidence.all_objects.count(),
                 Validation.all_objects.count())
        self.assertEqual(before, after)  # nada duplicado
        self.assertTrue(Evidence.objects.filter(code='EVID-002').exists())
        self.assertEqual(Validation.objects.count(), 1)

    def test_seed_does_not_duplicate_a_deleted_activity(self):
        call_command('seed_sgr', verbosity=0)
        for code in list(Evidence.objects.values_list('code', flat=True)):
            Evidence.objects.get(code=code).soft_delete()
        Activity.objects.all().delete()
        call_command('seed_sgr', verbosity=0)
        self.assertEqual(Activity.all_objects.count(), 2)
        self.assertEqual(Activity.objects.count(), 2)
