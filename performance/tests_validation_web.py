"""Pruebas del CRUD web de Validation (Fase 6, paso 6.3).

Se prueba por HTTP (Client), contra las URLs reales, igual que 6.1. Las fechas
son relativas a "hoy" para que la suite no dependa del día en que se corra.
Correr con:  python manage.py test performance.tests_validation_web
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from organization.models import Delegation, Employee, Position
from performance.forms import ValidationForm
from performance.models import Activity, CatalogItem, Evidence, Period, Validation

User = get_user_model()

VALIDATION_PERMS = ('view_validation', 'add_validation', 'change_validation')


def _perms(user, *codenames):
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label='performance', codename=codename)
        )


class ValidationWebTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        cls.evidence_date = cls.today - timedelta(days=10)
        cls.review_date = cls.today - timedelta(days=2)

        cls.deleg_a = Delegation.objects.create(id='DEL-A', name='Delegación A', scope='x')
        cls.deleg_b = Delegation.objects.create(id='DEL-B', name='Delegación B', scope='x')
        position = Position.objects.create(name='Cargo')
        verifier_group, _ = Group.objects.get_or_create(name='Verificador')

        def make_user(username, *, perms=(), group=None, delegation=None, name=None):
            user = User.objects.create_user(username, password='x')
            _perms(user, *perms)
            if group:
                user.groups.add(group)
            employee = None
            if delegation:
                employee = Employee.objects.create(
                    institutional_id=f'EMP-{username}', user=user,
                    delegation=delegation, position=position,
                    name=name or username)
            return user, employee

        # Verificador de A: mismo perfil que el grupo Verificador del seed.
        cls.verif_a, cls.emp_verif_a = make_user(
            'verif_a', perms=VALIDATION_PERMS, group=verifier_group,
            delegation=cls.deleg_a, name='Verificador Uno')
        cls.verif_a2, cls.emp_verif_a2 = make_user(
            'verif_a2', perms=VALIDATION_PERMS, group=verifier_group,
            delegation=cls.deleg_a, name='Verificador Dos')
        cls.verif_b, cls.emp_verif_b = make_user(
            'verif_b', perms=VALIDATION_PERMS, group=verifier_group,
            delegation=cls.deleg_b, name='Verificador Beta')
        # Tiene los permisos de modelo pero NO es Verificador: ValidationAdmin
        # lo bloquea en alta y edición, y la web también.
        cls.no_role, cls.emp_no_role = make_user(
            'no_role', perms=VALIDATION_PERMS, delegation=cls.deleg_a,
            name='Sin Rol')
        cls.sin_permiso, _ = make_user(
            'sin_permiso', delegation=cls.deleg_a, name='Sin Permiso')
        # Verificador con permisos pero sin fila Employee (caso borde).
        cls.no_employee, _ = make_user(
            'no_employee', perms=VALIDATION_PERMS, group=verifier_group)
        cls.root = User.objects.create_superuser('root', 'r@x.cl', 'x')

        # Dueños de las actividades (no son verificadores).
        cls.func_a, cls.emp_func_a = make_user(
            'func_a', delegation=cls.deleg_a, name='Funcionaria Alfa')
        cls.func_b, cls.emp_func_b = make_user(
            'func_b', delegation=cls.deleg_b, name='Funcionario Beta')

        period = Period.objects.create(
            start_date='2000-01-01', end_date='2100-12-31', computable_days=200,
            status='abierto', amber_threshold='70.00', collective_threshold='90.00')
        attention, _ = CatalogItem.objects.get_or_create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Atención test')

        def make_activity(employee, tag):
            return Activity.objects.create(
                employee=employee, period=period, attention=attention,
                activity_type='Primera Atención', service='s', sub_attention='sa',
                date=cls.evidence_date, request_description=f'sol {tag}',
                action_taken='a', status='Pendiente')

        cls.act_a = make_activity(cls.emp_func_a, 'A')
        cls.act_b = make_activity(cls.emp_func_b, 'B')

        def make_evidence(code, activity, file='evidence/x.pdf'):
            return Evidence.objects.create(
                code=code, activity=activity, file=file, date=cls.evidence_date)

        # Sin validación (candidatas a validar).
        cls.ev_a1 = make_evidence('EV-A1', cls.act_a)
        cls.ev_a2 = make_evidence('EV-A2', cls.act_a)
        cls.ev_a3 = make_evidence('EV-A3', cls.act_a)
        cls.ev_b1 = make_evidence('EV-B1', cls.act_b)
        # Con validación previa.
        cls.ev_a_done = make_evidence('EV-A-DONE', cls.act_a)
        cls.ev_b_done = make_evidence('EV-B-DONE', cls.act_b)

        cls.val_a = Validation.objects.create(
            evidence=cls.ev_a_done, employee=cls.emp_verif_a, decision='Aprobada',
            date=cls.review_date, result=True, notes='conforme')
        cls.val_b = Validation.objects.create(
            evidence=cls.ev_b_done, employee=cls.emp_verif_b, decision='Aprobada',
            date=cls.review_date, result=True)

    def payload(self, evidence=None, employee=None, **overrides):
        data = {
            'evidence': (evidence or self.ev_a1).pk,
            'employee': (employee or self.emp_verif_a).pk,
            'decision': 'Aprobada',
            'date': self.review_date.isoformat(),
            'notes': '',
        }
        data.update(overrides)
        return data


class ValidationListTests(ValidationWebTestData):
    url = reverse('performance:validation_list')

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_user_without_view_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_verifier_sees_only_own_delegation(self):
        self.client.force_login(self.verif_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['validations']), [self.val_a])
        self.assertNotContains(response, 'Verificador Beta')

    def test_superuser_sees_all(self):
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertCountEqual(response.context['validations'], [self.val_a, self.val_b])

    def test_user_without_employee_sees_nothing(self):
        self.client.force_login(self.no_employee)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['validations']), [])

    def test_soft_deleted_validation_is_not_listed(self):
        self.val_a.soft_delete()
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['validations']), [self.val_b])

    def test_view_permission_alone_is_enough_to_list(self):
        # Igual que el Admin: el rol se exige para crear y editar, no para ver.
        self.client.force_login(self.no_role)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['validations']), [self.val_a])

    def test_buttons_need_permission_and_reviewer_role(self):
        create_url = reverse('performance:validation_create')
        edit_url = reverse('performance:validation_update', args=[self.val_a.pk])
        self.client.force_login(self.verif_a)
        response = self.client.get(self.url)
        self.assertContains(response, create_url)
        self.assertContains(response, edit_url)
        # Permiso sin rol: ve el listado pero no los botones.
        self.client.force_login(self.no_role)
        response = self.client.get(self.url)
        self.assertNotContains(response, create_url)
        self.assertNotContains(response, edit_url)

    def test_decision_badge_reflects_result(self):
        Validation.objects.create(
            evidence=self.ev_a1, employee=self.emp_verif_a, decision='Rechazada',
            date=self.review_date, result=False, notes='ilegible')
        self.client.force_login(self.verif_a)
        response = self.client.get(self.url)
        self.assertContains(response, 'badge-ok')
        self.assertContains(response, 'badge-err')

    def test_paginates_with_page_size_from_url(self):
        for i in range(7):
            evidence = Evidence.objects.create(
                code=f'EV-P{i}', activity=self.act_a, file='evidence/x.pdf',
                date=self.evidence_date)
            Validation.objects.create(
                evidence=evidence, employee=self.emp_verif_a, decision='Aprobada',
                date=self.review_date, result=True)
        self.client.force_login(self.verif_a)
        response = self.client.get(self.url, {'per_page': 5})
        self.assertEqual(len(response.context['validations']), 5)
        self.assertTrue(response.context['page_obj'].has_next())
        page2 = self.client.get(self.url, {'page': 2})  # el tamaño quedó en sesión
        self.assertEqual(len(page2.context['validations']), 3)  # 8 en total (1 + 7)

    def test_invalid_page_size_is_normalized_not_an_error(self):
        self.client.force_login(self.verif_a)
        self.assertEqual(self.client.get(self.url, {'per_page': 99}).status_code, 200)


class ValidationCreateTests(ValidationWebTestData):
    url = reverse('performance:validation_create')

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_user_without_add_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        before = Validation.objects.count()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)
        self.assertEqual(Validation.objects.count(), before)

    def test_permission_without_reviewer_role_gets_403(self):
        # La regla de ValidationAdmin.has_add_permission que el permiso de
        # modelo, por sí solo, no cubre.
        self.client.force_login(self.no_role)
        before = Validation.objects.count()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)
        self.assertEqual(Validation.objects.count(), before)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.verif_a)
        before = Validation.objects.count()
        self.assertEqual(client.post(self.url, self.payload()).status_code, 403)
        self.assertEqual(Validation.objects.count(), before)

    def test_verifier_creates_approval(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse('performance:validation_list'))
        validation = Validation.objects.get(evidence=self.ev_a1)
        self.assertEqual(validation.employee, self.emp_verif_a)
        self.assertEqual(validation.decision, 'Aprobada')
        self.assertTrue(validation.result)
        self.assertEqual(validation.version, 1)

    def test_result_is_derived_from_decision(self):
        self.client.force_login(self.verif_a)
        self.client.post(self.url, self.payload(
            evidence=self.ev_a1, decision='Rechazada', notes='Archivo ilegible'))
        self.client.post(self.url, self.payload(
            evidence=self.ev_a2, decision='Corrección solicitada', notes='Falta la firma'))
        self.assertFalse(Validation.objects.get(evidence=self.ev_a1).result)
        self.assertFalse(Validation.objects.get(evidence=self.ev_a2).result)

    def test_form_has_no_result_or_version_field(self):
        # `result` se deriva y `version` no se edita (Decisión 24): ni siquiera
        # enviándolos a mano en el POST pueden llegar al modelo.
        self.client.force_login(self.verif_a)
        self.client.post(self.url, self.payload(
            decision='Rechazada', notes='motivo', result='on', version='9'))
        validation = Validation.objects.get(evidence=self.ev_a1)
        self.assertFalse(validation.result)
        self.assertEqual(validation.version, 1)

    def test_rejection_and_correction_require_notes(self):
        self.client.force_login(self.verif_a)
        before = Validation.objects.count()
        for decision in ('Rechazada', 'Corrección solicitada'):
            for notes in ('', '   '):
                response = self.client.post(self.url, self.payload(
                    decision=decision, notes=notes))
                self.assertEqual(response.status_code, 200)
                self.assertIn('notes', response.context['form'].errors)
        self.assertEqual(Validation.objects.count(), before)

    def test_approval_does_not_require_notes(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(notes=''))
        self.assertEqual(response.status_code, 302)

    def test_required_fields_are_enforced(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, {})
        errors = response.context['form'].errors
        for field in ('evidence', 'employee', 'decision', 'date'):
            self.assertIn(field, errors)

    def test_decision_outside_the_options_is_rejected(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(decision='Quizás'))
        self.assertIn('decision', response.context['form'].errors)

    def test_future_date_is_rejected(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(
            date=(self.today + timedelta(days=1)).isoformat()))
        self.assertEqual(response.status_code, 200)
        self.assertIn('date', response.context['form'].errors)

    def test_today_is_accepted(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(date=self.today.isoformat()))
        self.assertEqual(response.status_code, 302)

    def test_date_before_evidence_is_rejected(self):
        self.client.force_login(self.verif_a)
        before = Validation.objects.count()
        response = self.client.post(self.url, self.payload(
            date=(self.evidence_date - timedelta(days=1)).isoformat()))
        self.assertIn('date', response.context['form'].errors)
        self.assertEqual(Validation.objects.count(), before)

    def test_same_day_as_evidence_is_accepted(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(
            date=self.evidence_date.isoformat()))
        self.assertEqual(response.status_code, 302)

    def test_evidence_of_other_delegation_is_rejected(self):
        # El bypass que el scoping de la vista, por sí solo, no cierra.
        self.client.force_login(self.verif_a)
        before = Validation.objects.count()
        response = self.client.post(self.url, self.payload(evidence=self.ev_b1))
        self.assertEqual(response.status_code, 200)
        self.assertIn('evidence', response.context['form'].errors)
        self.assertEqual(Validation.objects.count(), before)

    def test_employee_of_other_delegation_is_rejected(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(employee=self.emp_verif_b))
        self.assertIn('employee', response.context['form'].errors)
        self.assertFalse(Validation.objects.filter(evidence=self.ev_a1).exists())

    def test_employee_who_is_not_verifier_is_rejected(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(employee=self.emp_func_a))
        self.assertIn('employee', response.context['form'].errors)

    def test_already_validated_evidence_is_rejected_with_clear_message(self):
        self.client.force_login(self.verif_a)
        before = Validation.objects.count()
        response = self.client.post(self.url, self.payload(evidence=self.ev_a_done))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ya tiene una validación')
        self.assertEqual(Validation.objects.count(), before)

    def test_double_submit_does_not_create_two_validations(self):
        self.client.force_login(self.verif_a)
        first = self.client.post(self.url, self.payload())
        second = self.client.post(self.url, self.payload())
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Validation.objects.filter(evidence=self.ev_a1).count(), 1)

    def test_evidence_whose_validation_was_deleted_stays_taken(self):
        # La fila eliminada sigue ocupando el 1:0..1; no se puede crear otra
        # (sería un IntegrityError, pantalla 500). Se responde como error de
        # formulario.
        self.val_a.soft_delete()
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(evidence=self.ev_a_done))
        self.assertEqual(response.status_code, 200)
        self.assertIn('evidence', response.context['form'].errors)

    def test_evidence_without_file_is_rejected(self):
        empty = Evidence.objects.create(
            code='EV-EMPTY', activity=self.act_a, file='', date=self.evidence_date)
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(evidence=empty))
        self.assertIn('evidence', response.context['form'].errors)
        self.assertContains(response, 'no tiene archivo')

    def test_soft_deleted_evidence_is_not_offered(self):
        self.ev_a1.soft_delete()
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url, self.payload(evidence=self.ev_a1))
        self.assertIn('evidence', response.context['form'].errors)

    def test_verifier_without_employee_cannot_create(self):
        self.client.force_login(self.no_employee)
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertIn('evidence', response.context['form'].errors)
        self.assertFalse(Validation.objects.filter(evidence=self.ev_a1).exists())

    def test_superuser_can_pick_any_verifier(self):
        # Igual que en el Admin (y que el seed, que deja una validación de
        # Norte a nombre del verificador de Centro): sin restricción de
        # Delegación para el superuser.
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload(employee=self.emp_verif_b))
        self.assertEqual(response.status_code, 302)

    def test_form_prefills_own_employee_and_today(self):
        self.client.force_login(self.verif_a)
        form = self.client.get(self.url).context['form']
        self.assertEqual(form.initial['employee'], self.emp_verif_a.pk)
        self.assertEqual(form.initial['date'], self.today)

    def test_page_offers_only_pending_evidence_of_own_delegation(self):
        self.client.force_login(self.verif_a)
        response = self.client.get(self.url)
        self.assertContains(response, 'EV-A1')
        self.assertNotContains(response, 'EV-A-DONE')
        self.assertNotContains(response, 'EV-B1')


class ValidationUpdateTests(ValidationWebTestData):
    def url(self, validation):
        return reverse('performance:validation_update', args=[validation.pk])

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url(self.val_a))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={self.url(self.val_a)}")

    def test_user_without_change_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.get(self.url(self.val_a)).status_code, 403)

    def test_permission_without_reviewer_role_gets_403(self):
        self.client.force_login(self.no_role)
        self.assertEqual(self.client.get(self.url(self.val_a)).status_code, 403)
        response = self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a_done, decision='Rechazada', notes='x'))
        self.assertEqual(response.status_code, 403)
        self.val_a.refresh_from_db()
        self.assertEqual(self.val_a.decision, 'Aprobada')

    def test_edits_own_delegation_validation(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a_done, decision='Rechazada', notes='Se detectó un error'))
        self.assertRedirects(response, reverse('performance:validation_list'))
        self.val_a.refresh_from_db()
        self.assertEqual(self.val_a.decision, 'Rechazada')
        self.assertFalse(self.val_a.result)
        self.assertEqual(self.val_a.notes, 'Se detectó un error')

    def test_editing_rejection_back_to_approval_updates_result(self):
        self.client.force_login(self.verif_a)
        self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a_done, decision='Rechazada', notes='x'))
        self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a_done, decision='Aprobada'))
        self.val_a.refresh_from_db()
        self.assertTrue(self.val_a.result)

    def test_rejecting_without_notes_is_an_error(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a_done, decision='Rechazada', notes=''))
        self.assertEqual(response.status_code, 200)
        self.assertIn('notes', response.context['form'].errors)
        self.val_a.refresh_from_db()
        self.assertEqual(self.val_a.decision, 'Aprobada')

    def test_form_prefilled_and_evidence_is_read_only(self):
        self.client.force_login(self.verif_a)
        response = self.client.get(self.url(self.val_a))
        form = response.context['form']
        self.assertEqual(form.initial['decision'], 'Aprobada')
        self.assertTrue(form.fields['evidence'].disabled)
        self.assertContains(response, f'value="{self.review_date.isoformat()}"')

    def test_evidence_cannot_be_changed_by_editing_the_post(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a2))  # otra evidencia pendiente de la misma Delegación
        self.assertEqual(response.status_code, 302)
        self.val_a.refresh_from_db()
        self.assertEqual(self.val_a.evidence, self.ev_a_done)
        self.assertFalse(Validation.objects.filter(evidence=self.ev_a2).exists())

    def test_version_is_not_touched_by_editing(self):
        self.client.force_login(self.verif_a)
        self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a_done, version='7'))
        self.val_a.refresh_from_db()
        self.assertEqual(self.val_a.version, 1)

    def test_other_delegation_validation_is_404(self):
        self.client.force_login(self.verif_a)
        self.assertEqual(self.client.get(self.url(self.val_b)).status_code, 404)
        response = self.client.post(self.url(self.val_b), self.payload(
            evidence=self.ev_b_done, employee=self.emp_verif_b,
            decision='Rechazada', notes='x'))
        self.assertEqual(response.status_code, 404)
        self.val_b.refresh_from_db()
        self.assertEqual(self.val_b.decision, 'Aprobada')

    def test_cannot_reassign_to_verifier_of_other_delegation(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a_done, employee=self.emp_verif_b))
        self.assertEqual(response.status_code, 200)
        self.assertIn('employee', response.context['form'].errors)
        self.val_a.refresh_from_db()
        self.assertEqual(self.val_a.employee, self.emp_verif_a)

    def test_saving_without_changes_works(self):
        self.client.force_login(self.verif_a)
        response = self.client.post(self.url(self.val_a), self.payload(
            evidence=self.ev_a_done, notes='conforme'))
        self.assertEqual(response.status_code, 302)

    def test_soft_deleted_validation_is_404(self):
        self.val_a.soft_delete()
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.url(self.val_a)).status_code, 404)

    def test_superuser_edits_validation_of_any_delegation(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url(self.val_b), self.payload(
            evidence=self.ev_b_done, employee=self.emp_verif_b,
            decision='Corrección solicitada', notes='Falta el sello'))
        self.assertEqual(response.status_code, 302)
        self.val_b.refresh_from_db()
        self.assertEqual(self.val_b.decision, 'Corrección solicitada')


class ValidationFormScopingTests(ValidationWebTestData):
    def test_evidence_choices_limited_to_pending_of_own_delegation(self):
        form = ValidationForm(user=self.verif_a)
        self.assertCountEqual(
            form.fields['evidence'].queryset, [self.ev_a1, self.ev_a2, self.ev_a3])

    def test_employee_choices_limited_to_verifiers_of_own_delegation(self):
        form = ValidationForm(user=self.verif_a)
        self.assertCountEqual(
            form.fields['employee'].queryset, [self.emp_verif_a, self.emp_verif_a2])

    def test_superuser_gets_all_pending_evidence_and_all_verifiers(self):
        form = ValidationForm(user=self.root)
        self.assertCountEqual(
            form.fields['evidence'].queryset,
            [self.ev_a1, self.ev_a2, self.ev_a3, self.ev_b1])
        self.assertCountEqual(
            form.fields['employee'].queryset,
            [self.emp_verif_a, self.emp_verif_a2, self.emp_verif_b])

    def test_user_without_employee_gets_empty_choices(self):
        form = ValidationForm(user=self.no_employee)
        self.assertEqual(list(form.fields['evidence'].queryset), [])
        self.assertEqual(list(form.fields['employee'].queryset), [])

    def test_editing_offers_only_its_own_evidence(self):
        form = ValidationForm(instance=self.val_a, user=self.verif_a)
        self.assertEqual(list(form.fields['evidence'].queryset), [self.ev_a_done])
        self.assertTrue(form.fields['evidence'].disabled)

    def test_evidence_with_deleted_validation_is_not_offered(self):
        self.val_a.soft_delete()
        form = ValidationForm(user=self.verif_a)
        self.assertNotIn(self.ev_a_done, form.fields['evidence'].queryset)

    def test_superuser_without_employee_has_no_employee_prefill(self):
        form = ValidationForm(user=self.root)
        self.assertNotIn('employee', form.initial)
        self.assertEqual(form.initial['date'], self.today)
