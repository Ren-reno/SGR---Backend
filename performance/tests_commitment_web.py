"""Pruebas del CRUD web de Commitment (Fase 6, paso 6.4).

Se prueba por HTTP (Client), contra las URLs reales, igual que en 6.1.
Correr con:  python manage.py test performance.tests_commitment_web
"""
import warnings
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.paginator import UnorderedObjectListWarning
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from organization.models import Delegation, Employee, Position
from performance.forms import CommitmentForm
from performance.models import Commitment

User = get_user_model()


def _perms(user, *codenames):
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label='performance', codename=codename)
        )


class CommitmentWebTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        cls.future = cls.today + timedelta(days=30)

        cls.deleg_a = Delegation.objects.create(id='DEL-A', name='Delegación A', scope='x')
        cls.deleg_b = Delegation.objects.create(id='DEL-B', name='Delegación B', scope='x')
        position = Position.objects.create(name='Cargo')

        # Funcionario A: mismo perfil de permisos que el grupo Funcionario
        # del seed sobre Commitment (ver, crear y editar; no borrar).
        cls.func_a = User.objects.create_user('func_a', password='x')
        _perms(cls.func_a, 'view_commitment', 'add_commitment', 'change_commitment')
        # Mismo perfil que el grupo Verificador del seed: sin ningún permiso
        # sobre Commitment (Decisión 18), aunque sí los tiene sobre lo demás.
        cls.verifier = User.objects.create_user('verif', password='x')
        _perms(cls.verifier, 'view_activity', 'change_activity', 'view_evidence',
               'change_evidence', 'view_validation', 'add_validation',
               'change_validation')
        # Sin ningún permiso de modelo (como el grupo Delegado hoy).
        cls.sin_permiso = User.objects.create_user('sin_permiso', password='x')
        cls.root = User.objects.create_superuser('root', 'r@x.cl', 'x')
        user_a2 = User.objects.create_user('func_a2', password='x')
        user_b = User.objects.create_user('func_b', password='x')

        cls.emp_a = Employee.objects.create(
            institutional_id='EMP-A', user=cls.func_a, delegation=cls.deleg_a,
            position=position, name='Empleado A')
        cls.emp_a2 = Employee.objects.create(
            institutional_id='EMP-A2', user=user_a2, delegation=cls.deleg_a,
            position=position, name='Empleado A2')
        cls.emp_b = Employee.objects.create(
            institutional_id='EMP-B', user=user_b, delegation=cls.deleg_b,
            position=position, name='Empleado B')
        Employee.objects.create(
            institutional_id='EMP-V', user=cls.verifier, delegation=cls.deleg_a,
            position=position, name='Verificador A')

        cls.com_a = cls._make(cls.emp_a, 'Solicitud vecinal')
        cls.com_b = cls._make(cls.emp_b, 'Solicitud B')

    @classmethod
    def _make(cls, employee, origin, due_date=None, **extra):
        return Commitment.objects.create(
            delegation=employee.delegation, responsible=employee, origin=origin,
            requester='Juan Pérez', territory='Sector Norte',
            due_date=due_date or cls.future, **extra)

    def payload(self, delegation=None, responsible=None, **overrides):
        data = {
            'delegation': (self.deleg_a if delegation is None else delegation).pk,
            'responsible': (self.emp_a if responsible is None else responsible).pk,
            'origin': 'Reclamo por luminaria',
            'requester': 'María Soto',
            'territory': 'Sector Sur',
            'due_date': self.future.isoformat(),
            'support_area': '',
            'status': Commitment.STATUS_INGRESADO,
            'observation': '',
        }
        data.update(overrides)
        return data

    def user_with(self, username, *codenames):
        """Usuario de la Delegación A con SOLO esos permisos de Commitment."""
        user = User.objects.create_user(username, password='x')
        _perms(user, *codenames)
        Employee.objects.create(
            institutional_id=f'EMP-{username}', user=user, delegation=self.deleg_a,
            position=Position.objects.first(), name=username)
        return user


class CommitmentListTests(CommitmentWebTestData):
    url = reverse('performance:commitment_list')

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_user_without_view_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_verifier_profile_gets_403(self):
        # Decisión 18: un compromiso no es una evidencia.
        self.client.force_login(self.verifier)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_add_and_change_permissions_do_not_grant_view(self):
        user = self.user_with('sin_ver', 'add_commitment', 'change_commitment')
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_user_sees_only_own_delegation(self):
        self.client.force_login(self.func_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['commitments']), [self.com_a])
        self.assertNotContains(response, 'Solicitud B')

    def test_superuser_sees_all(self):
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertCountEqual(response.context['commitments'], [self.com_a, self.com_b])

    def test_scope_uses_commitment_delegation_not_current_responsible(self):
        # Decisión 18: se acota por la Delegación del propio compromiso. Si
        # el responsable pasara a otra Delegación, sigue visible para la
        # que lo originó.
        Commitment.objects.filter(pk=self.com_a.pk).update(responsible=self.emp_b)
        self.client.force_login(self.func_a)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['commitments']), [self.com_a])

    def test_soft_deleted_commitment_is_not_listed(self):
        self.com_a.soft_delete()
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['commitments']), [self.com_b])

    def test_status_is_shown_with_its_label(self):
        Commitment.objects.filter(pk=self.com_a.pk).update(
            status=Commitment.STATUS_EN_PROCESO)
        self.client.force_login(self.func_a)
        self.assertContains(self.client.get(self.url), 'En proceso')

    def test_add_and_edit_buttons_follow_permissions(self):
        create_url = reverse('performance:commitment_create')
        edit_url = reverse('performance:commitment_update', args=[self.com_a.pk])
        only_view = User.objects.create_user('solo_ver', password='x')
        _perms(only_view, 'view_commitment')
        Employee.objects.create(
            institutional_id='EMP-SV', user=only_view, delegation=self.deleg_a,
            position=Position.objects.first(), name='Solo ver')
        self.client.force_login(only_view)
        response = self.client.get(self.url)
        self.assertNotContains(response, create_url)
        self.assertNotContains(response, edit_url)
        self.client.force_login(self.func_a)
        response = self.client.get(self.url)
        self.assertContains(response, create_url)
        self.assertContains(response, edit_url)

    def test_paginates_with_page_size_from_url(self):
        for i in range(7):
            self._make(self.emp_a, f'extra {i}')
        self.client.force_login(self.func_a)
        response = self.client.get(self.url, {'per_page': 5})
        self.assertEqual(len(response.context['commitments']), 5)
        self.assertTrue(response.context['page_obj'].has_next())
        page2 = self.client.get(self.url, {'page': 2})  # el tamaño quedó en sesión
        self.assertEqual(len(page2.context['commitments']), 3)

    def test_paginated_list_is_ordered(self):
        # Sin `ordering`, Paginator emite UnorderedObjectListWarning.
        for i in range(7):
            self._make(self.emp_a, f'extra {i}')
        self.client.force_login(self.func_a)
        with warnings.catch_warnings():
            warnings.simplefilter('error', UnorderedObjectListWarning)
            response = self.client.get(self.url, {'per_page': 5})
        self.assertEqual(response.status_code, 200)

    def test_invalid_per_page_is_ignored_without_error(self):
        self.client.force_login(self.func_a)
        for value in ('99', 'abc', '-5'):
            self.assertEqual(self.client.get(self.url, {'per_page': value}).status_code, 200)


class CommitmentCreateTests(CommitmentWebTestData):
    url = reverse('performance:commitment_create')

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_user_without_add_permission_gets_403(self):
        for user in (self.sin_permiso, self.verifier):
            self.client.force_login(user)
            before = Commitment.objects.count()
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)
            self.assertEqual(Commitment.objects.count(), before)

    def test_view_and_change_permissions_do_not_grant_add(self):
        # El perfil de Activity en el seed: ve y edita, pero no crea.
        user = self.user_with('sin_add', 'view_commitment', 'change_commitment')
        self.client.force_login(user)
        before = Commitment.objects.count()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)
        self.assertEqual(Commitment.objects.count(), before)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.func_a)
        before = Commitment.objects.count()
        self.assertEqual(client.post(self.url, self.payload()).status_code, 403)
        self.assertEqual(Commitment.objects.count(), before)

    def test_funcionario_creates_commitment_in_own_delegation(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse('performance:commitment_list'))
        created = Commitment.objects.get(origin='Reclamo por luminaria')
        self.assertEqual(created.delegation, self.deleg_a)
        self.assertEqual(created.status, Commitment.STATUS_INGRESADO)

    def test_success_message_is_shown(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload(), follow=True)
        self.assertContains(response, 'Compromiso registrado.')

    def test_superuser_creates_commitment_in_any_delegation(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload(
            delegation=self.deleg_b, responsible=self.emp_b))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Commitment.objects.filter(
            origin='Reclamo por luminaria', delegation=self.deleg_b).exists())

    def test_own_delegation_is_preselected_for_regular_user(self):
        self.client.force_login(self.func_a)
        response = self.client.get(self.url)
        self.assertContains(response, '<option value="DEL-A" selected>')

    def test_no_delegation_is_preselected_for_superuser(self):
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertNotContains(response, '<option value="DEL-A" selected>')

    def test_required_fields_are_enforced(self):
        self.client.force_login(self.func_a)
        before = Commitment.objects.count()
        response = self.client.post(self.url, self.payload(
            origin='   ', requester='', territory='', due_date=''))
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        for field in ('origin', 'requester', 'territory', 'due_date'):
            self.assertIn(field, errors)
        self.assertEqual(Commitment.objects.count(), before)

    def test_delegation_and_responsible_are_required(self):
        self.client.force_login(self.func_a)
        data = self.payload()
        data.update(delegation='', responsible='')
        response = self.client.post(self.url, data)
        errors = response.context['form'].errors
        self.assertIn('delegation', errors)
        self.assertIn('responsible', errors)

    def test_status_outside_the_four_values_is_rejected(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload(status='cerrado'))
        self.assertIn('status', response.context['form'].errors)

    def test_optional_fields_can_be_left_empty(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload(support_area='', observation=''))
        self.assertEqual(response.status_code, 302)

    def test_past_due_date_is_rejected(self):
        self.client.force_login(self.func_a)
        before = Commitment.objects.count()
        yesterday = (self.today - timedelta(days=1)).isoformat()
        response = self.client.post(self.url, self.payload(due_date=yesterday))
        self.assertEqual(response.status_code, 200)
        self.assertIn('due_date', response.context['form'].errors)
        self.assertEqual(Commitment.objects.count(), before)

    def test_due_date_today_is_accepted(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload(due_date=self.today.isoformat()))
        self.assertEqual(response.status_code, 302)

    def test_malformed_due_date_is_rejected(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload(due_date='31/02/2026'))
        self.assertIn('due_date', response.context['form'].errors)

    def test_responsible_must_belong_to_the_delegation(self):
        # Regla de negocio de Commitment.clean() (Decisión 17). Solo un
        # superuser puede llegar acá: para el resto, el desplegable ya
        # acota ambos campos a su Delegación.
        self.client.force_login(self.root)
        before = Commitment.objects.count()
        response = self.client.post(self.url, self.payload(
            delegation=self.deleg_a, responsible=self.emp_b))
        self.assertEqual(response.status_code, 200)
        self.assertIn('delegation', response.context['form'].errors)
        self.assertEqual(Commitment.objects.count(), before)

    def test_cannot_create_in_other_delegation(self):
        # El bypass que el scoping de la vista, por sí solo, no cierra.
        self.client.force_login(self.func_a)
        before = Commitment.objects.count()
        response = self.client.post(self.url, self.payload(
            delegation=self.deleg_b, responsible=self.emp_b))
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        self.assertIn('delegation', errors)
        self.assertIn('responsible', errors)
        self.assertEqual(Commitment.objects.count(), before)

    def test_cannot_assign_responsible_of_other_delegation(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload(responsible=self.emp_b))
        self.assertIn('responsible', response.context['form'].errors)

    def test_duplicate_is_rejected(self):
        self.client.force_login(self.func_a)
        dup = self.payload(
            origin='SOLICITUD VECINAL', requester='juan pérez',
            territory='sector norte', due_date=self.future.isoformat())
        before = Commitment.objects.count()
        response = self.client.post(self.url, dup)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertEqual(Commitment.objects.count(), before)

    def test_same_data_with_other_responsible_is_not_a_duplicate(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload(
            responsible=self.emp_a2, origin='Solicitud vecinal',
            requester='Juan Pérez', territory='Sector Norte'))
        self.assertEqual(response.status_code, 302)

    def test_duplicate_check_ignores_soft_deleted(self):
        self.com_a.soft_delete()
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload(
            origin='Solicitud vecinal', requester='Juan Pérez',
            territory='Sector Norte'))
        self.assertEqual(response.status_code, 302)


class CommitmentUpdateTests(CommitmentWebTestData):
    def url(self, commitment):
        return reverse('performance:commitment_update', args=[commitment.pk])

    def update_payload(self, **overrides):
        """Los valores actuales de `com_a`, con los cambios indicados."""
        return self.payload(
            origin='Solicitud vecinal', requester='Juan Pérez',
            territory='Sector Norte', **overrides)

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url(self.com_a))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={self.url(self.com_a)}")

    def test_user_without_change_permission_gets_403(self):
        for user in (self.sin_permiso, self.verifier):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url(self.com_a)).status_code, 403)
            self.assertEqual(
                self.client.post(self.url(self.com_a), self.update_payload()).status_code, 403)

    def test_view_and_add_permissions_do_not_grant_change(self):
        user = self.user_with('sin_change', 'view_commitment', 'add_commitment')
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url(self.com_a)).status_code, 403)
        response = self.client.post(
            self.url(self.com_a), self.update_payload(observation='no debería'))
        self.assertEqual(response.status_code, 403)
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.observation, '')

    def test_edits_own_delegation_commitment(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.com_a), self.update_payload(
            status=Commitment.STATUS_EN_PROCESO, observation='Se coordinó visita'))
        self.assertRedirects(response, reverse('performance:commitment_list'))
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.status, Commitment.STATUS_EN_PROCESO)
        self.assertEqual(self.com_a.observation, 'Se coordinó visita')

    def test_success_message_is_shown(self):
        self.client.force_login(self.func_a)
        response = self.client.post(
            self.url(self.com_a), self.update_payload(), follow=True)
        self.assertContains(response, 'Compromiso actualizado.')

    def test_form_prefilled_with_current_values(self):
        self.client.force_login(self.func_a)
        response = self.client.get(self.url(self.com_a))
        self.assertContains(response, 'value="Solicitud vecinal"')
        self.assertContains(response, f'value="{self.future.isoformat()}"')

    def test_other_delegation_commitment_is_404(self):
        self.client.force_login(self.func_a)
        self.assertEqual(self.client.get(self.url(self.com_b)).status_code, 404)
        response = self.client.post(self.url(self.com_b), self.payload(
            delegation=self.deleg_b, responsible=self.emp_b, origin='hackeado'))
        self.assertEqual(response.status_code, 404)
        self.com_b.refresh_from_db()
        self.assertEqual(self.com_b.origin, 'Solicitud B')

    def test_cannot_move_commitment_to_other_delegation(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.com_a), self.update_payload(
            delegation=self.deleg_b, responsible=self.emp_b))
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        self.assertIn('delegation', errors)
        self.assertIn('responsible', errors)
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.delegation, self.deleg_a)
        self.assertEqual(self.com_a.responsible, self.emp_a)

    def test_cannot_assign_responsible_of_other_delegation(self):
        self.client.force_login(self.func_a)
        response = self.client.post(
            self.url(self.com_a), self.update_payload(responsible=self.emp_b))
        self.assertIn('responsible', response.context['form'].errors)
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.responsible, self.emp_a)

    def test_can_reassign_responsible_within_own_delegation(self):
        self.client.force_login(self.func_a)
        response = self.client.post(
            self.url(self.com_a), self.update_payload(responsible=self.emp_a2))
        self.assertEqual(response.status_code, 302)
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.responsible, self.emp_a2)

    def test_saving_without_changes_is_not_a_duplicate_of_itself(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.com_a), self.update_payload())
        self.assertEqual(response.status_code, 302)

    def test_editing_into_another_existing_commitment_is_a_duplicate(self):
        other = self._make(self.emp_a, 'Otro origen')
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(other), self.update_payload())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())

    def test_overdue_commitment_stays_editable_without_touching_its_date(self):
        # Un compromiso vencido tiene que poder pasar a "Realizado".
        overdue = self._make(
            self.emp_a, 'Vencido', due_date=self.today - timedelta(days=10))
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(overdue), self.payload(
            origin='Vencido', requester='Juan Pérez', territory='Sector Norte',
            due_date=overdue.due_date.isoformat(),
            status=Commitment.STATUS_REALIZADO))
        self.assertEqual(response.status_code, 302)
        overdue.refresh_from_db()
        self.assertEqual(overdue.status, Commitment.STATUS_REALIZADO)

    def test_changing_due_date_to_the_past_is_rejected(self):
        self.client.force_login(self.func_a)
        past = (self.today - timedelta(days=3)).isoformat()
        response = self.client.post(self.url(self.com_a), self.update_payload(due_date=past))
        self.assertEqual(response.status_code, 200)
        self.assertIn('due_date', response.context['form'].errors)
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.due_date, self.future)

    def test_soft_deleted_commitment_is_404(self):
        self.com_a.soft_delete()
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.url(self.com_a)).status_code, 404)


class CommitmentFormScopingTests(CommitmentWebTestData):
    def test_delegation_choices_limited_to_own_delegation(self):
        form = CommitmentForm(user=self.func_a)
        self.assertEqual(list(form.fields['delegation'].queryset), [self.deleg_a])

    def test_responsible_choices_limited_to_own_delegation(self):
        form = CommitmentForm(user=self.func_a)
        self.assertEqual(
            list(form.fields['responsible'].queryset), [self.emp_a, self.emp_a2, Employee.objects.get(pk='EMP-V')])
        self.assertNotIn(self.emp_b, form.fields['responsible'].queryset)

    def test_superuser_gets_all_delegations_and_employees(self):
        form = CommitmentForm(user=self.root)
        self.assertCountEqual(
            form.fields['delegation'].queryset, [self.deleg_a, self.deleg_b])
        self.assertIn(self.emp_b, form.fields['responsible'].queryset)

    def test_user_without_employee_gets_empty_choices(self):
        # Sin Employee no hay Delegación contra la cual comparar: ninguna
        # opción, no todas (mismo criterio que el Admin, Bug 2 / Decisión 6).
        orphan = User.objects.create_user('orphan', password='x')
        _perms(orphan, 'view_commitment', 'add_commitment', 'change_commitment')
        form = CommitmentForm(user=orphan)
        self.assertFalse(form.fields['delegation'].queryset.exists())
        self.assertFalse(form.fields['responsible'].queryset.exists())

    def test_preselection_only_when_a_single_delegation_is_possible(self):
        self.assertEqual(CommitmentForm(user=self.func_a).initial['delegation'], 'DEL-A')
        self.assertIsNone(CommitmentForm(user=self.root).initial.get('delegation'))

    def test_editing_keeps_the_instance_delegation(self):
        form = CommitmentForm(instance=self.com_a, user=self.func_a)
        self.assertEqual(form.initial['delegation'], 'DEL-A')
