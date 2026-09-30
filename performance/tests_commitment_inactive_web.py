"""Pruebas de los desplegables de Commitment con registros inactivos (Fase 6,
ajuste 3.7, Decisión 32).

`CommitmentForm` ofrece solo Delegaciones y empleados con `is_active=True`, y
al editar conserva el valor que el compromiso ya tenía aunque hoy esté
inactivo. Se prueba a nivel de formulario (los `queryset` de los dos
desplegables) y por HTTP contra las URLs reales, igual que `tests_commitment_web`.
Correr con:  python manage.py test performance.tests_commitment_inactive_web
"""
from django.urls import reverse

from organization.models import Delegation, Employee
from performance.forms import CommitmentForm
from performance.models import Commitment
from performance.tests_commitment_web import CommitmentWebTestData, User, _perms


def deactivate(model, *pks):
    """Da de baja (`is_active=False`) con `update()`: no pasa por `save()` ni
    por ninguna validación, como lo haría un cambio hecho desde el Admin."""
    model.objects.filter(pk__in=pks).update(is_active=False)


class InactiveInFormChoicesTests(CommitmentWebTestData):
    """Los `queryset` de los dos desplegables, sin pasar por HTTP."""

    def test_inactive_employee_is_not_offered_as_responsible(self):
        deactivate(Employee, 'EMP-A2')
        form = CommitmentForm(user=self.func_a)
        responsible = form.fields['responsible'].queryset
        self.assertNotIn(self.emp_a2, responsible)
        self.assertIn(self.emp_a, responsible)

    def test_active_employees_are_still_offered(self):
        deactivate(Employee, 'EMP-A2')
        form = CommitmentForm(user=self.func_a)
        self.assertEqual(
            list(form.fields['responsible'].queryset),
            [self.emp_a, Employee.objects.get(pk='EMP-V')])

    def test_inactive_delegation_is_not_offered_to_superuser(self):
        deactivate(Delegation, 'DEL-B')
        form = CommitmentForm(user=self.root)
        self.assertEqual(list(form.fields['delegation'].queryset), [self.deleg_a])

    def test_inactive_employee_is_not_offered_to_superuser(self):
        deactivate(Employee, 'EMP-B')
        form = CommitmentForm(user=self.root)
        self.assertNotIn(self.emp_b, form.fields['responsible'].queryset)
        self.assertIn(self.emp_a, form.fields['responsible'].queryset)

    def test_own_inactive_delegation_leaves_no_delegation_to_choose(self):
        # Consecuencia de la regla: quien solo puede elegir su propia
        # Delegación y esta está inactiva, no puede registrar compromisos
        # nuevos (no hay nada que preseleccionar).
        deactivate(Delegation, 'DEL-A')
        form = CommitmentForm(user=self.func_a)
        self.assertFalse(form.fields['delegation'].queryset.exists())
        self.assertIsNone(form.initial.get('delegation'))

    def test_editing_keeps_the_current_inactive_responsible(self):
        deactivate(Employee, 'EMP-A')
        form = CommitmentForm(instance=self.com_a, user=self.func_a)
        responsible = form.fields['responsible'].queryset
        self.assertIn(self.emp_a, responsible)
        self.assertIn(self.emp_a2, responsible)

    def test_editing_keeps_the_current_inactive_delegation(self):
        deactivate(Delegation, 'DEL-A')
        form = CommitmentForm(instance=self.com_a, user=self.func_a)
        self.assertEqual(list(form.fields['delegation'].queryset), [self.deleg_a])

    def test_editing_does_not_keep_other_inactive_employees(self):
        # Solo se conserva el valor actual del compromiso, no todos los
        # inactivos.
        deactivate(Employee, 'EMP-A', 'EMP-A2')
        form = CommitmentForm(instance=self.com_a, user=self.func_a)
        responsible = form.fields['responsible'].queryset
        self.assertIn(self.emp_a, responsible)
        self.assertNotIn(self.emp_a2, responsible)

    def test_creating_does_not_keep_any_inactive_record(self):
        # Sin `pk` no hay valor actual que conservar.
        deactivate(Employee, 'EMP-A')
        form = CommitmentForm(user=self.func_a)
        self.assertNotIn(self.emp_a, form.fields['responsible'].queryset)

    def test_unsaved_instance_keeps_nothing(self):
        # `pk` distingue el alta de la edición: una instancia sin guardar que
        # ya trae valores (p. ej. precargados) no tiene un valor "actual" que
        # conservar.
        deactivate(Employee, 'EMP-A')
        unsaved = Commitment(delegation=self.deleg_a, responsible=self.emp_a)
        form = CommitmentForm(instance=unsaved, user=self.func_a)
        self.assertNotIn(self.emp_a, form.fields['responsible'].queryset)

    def test_kept_inactive_value_does_not_skip_scoping(self):
        # El valor conservado se suma DENTRO del scoping, no por encima: un
        # compromiso de otra Delegación no le abre sus datos inactivos a
        # quien no puede verlos (en la web esa edición ya responde 404; esto
        # protege al formulario por sí solo).
        deactivate(Delegation, 'DEL-B')
        deactivate(Employee, 'EMP-B')
        form = CommitmentForm(instance=self.com_b, user=self.func_a)
        self.assertNotIn(self.deleg_b, form.fields['delegation'].queryset)
        self.assertNotIn(self.emp_b, form.fields['responsible'].queryset)

    def test_kept_inactive_value_does_not_skip_the_no_employee_rule(self):
        # Sin Employee no hay Delegación contra la cual comparar: ninguna
        # opción, ni siquiera el valor actual del compromiso.
        deactivate(Delegation, 'DEL-A')
        deactivate(Employee, 'EMP-A')
        orphan = User.objects.create_user('orphan', password='x')
        _perms(orphan, 'view_commitment', 'change_commitment')
        form = CommitmentForm(instance=self.com_a, user=orphan)
        self.assertFalse(form.fields['delegation'].queryset.exists())
        self.assertFalse(form.fields['responsible'].queryset.exists())

    def test_superuser_editing_keeps_current_inactive_values(self):
        deactivate(Delegation, 'DEL-B')
        deactivate(Employee, 'EMP-B')
        form = CommitmentForm(instance=self.com_b, user=self.root)
        self.assertCountEqual(
            form.fields['delegation'].queryset, [self.deleg_a, self.deleg_b])
        self.assertIn(self.emp_b, form.fields['responsible'].queryset)


class InactiveCreateTests(CommitmentWebTestData):
    url = reverse('performance:commitment_create')

    def test_inactive_employee_is_not_in_the_rendered_form(self):
        deactivate(Employee, 'EMP-A2')
        self.client.force_login(self.func_a)
        response = self.client.get(self.url)
        self.assertContains(response, 'value="EMP-A"')
        self.assertNotContains(response, 'value="EMP-A2"')

    def test_cannot_create_with_an_inactive_responsible(self):
        # El servidor rechaza el valor aunque el POST lo envíe a mano.
        deactivate(Employee, 'EMP-A2')
        self.client.force_login(self.func_a)
        before = Commitment.objects.count()
        response = self.client.post(
            self.url, self.payload(responsible=self.emp_a2))
        self.assertEqual(response.status_code, 200)
        self.assertIn('responsible', response.context['form'].errors)
        self.assertEqual(Commitment.objects.count(), before)

    def test_can_still_create_with_an_active_responsible(self):
        deactivate(Employee, 'EMP-A2')
        self.client.force_login(self.func_a)
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse('performance:commitment_list'))
        self.assertTrue(
            Commitment.objects.filter(origin='Reclamo por luminaria').exists())

    def test_cannot_create_in_an_inactive_delegation(self):
        deactivate(Delegation, 'DEL-B')
        self.client.force_login(self.root)
        before = Commitment.objects.count()
        response = self.client.post(self.url, self.payload(
            delegation=self.deleg_b, responsible=self.emp_b))
        self.assertEqual(response.status_code, 200)
        self.assertIn('delegation', response.context['form'].errors)
        self.assertEqual(Commitment.objects.count(), before)

    def test_superuser_can_still_create_in_an_active_delegation(self):
        deactivate(Delegation, 'DEL-B')
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, 302)

    def test_regular_user_of_an_inactive_delegation_cannot_create(self):
        deactivate(Delegation, 'DEL-A')
        self.client.force_login(self.func_a)
        before = Commitment.objects.count()
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertIn('delegation', response.context['form'].errors)
        self.assertEqual(Commitment.objects.count(), before)


class InactiveUpdateTests(CommitmentWebTestData):
    def url(self, commitment):
        return reverse('performance:commitment_update', args=[commitment.pk])

    def update_payload(self, **overrides):
        """Los valores actuales de `com_a`, con los cambios indicados."""
        return self.payload(
            origin='Solicitud vecinal', requester='Juan Pérez',
            territory='Sector Norte', **overrides)

    def test_edit_form_still_renders_the_current_inactive_responsible(self):
        deactivate(Employee, 'EMP-A', 'EMP-A2')
        self.client.force_login(self.func_a)
        response = self.client.get(self.url(self.com_a))
        self.assertContains(response, 'value="EMP-A"')
        self.assertNotContains(response, 'value="EMP-A2"')

    def test_can_edit_a_commitment_whose_responsible_became_inactive(self):
        # El caso que motiva conservar el valor actual: sin esto, un
        # compromiso antiguo no se podría guardar ni para pasarlo a
        # "En proceso".
        deactivate(Employee, 'EMP-A')
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.com_a), self.update_payload(
            status=Commitment.STATUS_EN_PROCESO, observation='Se coordinó visita'))
        self.assertRedirects(response, reverse('performance:commitment_list'))
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.responsible, self.emp_a)
        self.assertEqual(self.com_a.status, Commitment.STATUS_EN_PROCESO)

    def test_can_edit_a_commitment_whose_delegation_became_inactive(self):
        deactivate(Delegation, 'DEL-A')
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.com_a), self.update_payload(
            observation='Sigue en gestión'))
        self.assertRedirects(response, reverse('performance:commitment_list'))
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.observation, 'Sigue en gestión')

    def test_can_move_from_an_inactive_responsible_to_an_active_one(self):
        deactivate(Employee, 'EMP-A')
        self.client.force_login(self.func_a)
        response = self.client.post(
            self.url(self.com_a), self.update_payload(responsible=self.emp_a2))
        self.assertEqual(response.status_code, 302)
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.responsible, self.emp_a2)

    def test_cannot_switch_to_another_inactive_responsible(self):
        deactivate(Employee, 'EMP-A', 'EMP-A2')
        self.client.force_login(self.func_a)
        response = self.client.post(
            self.url(self.com_a), self.update_payload(responsible=self.emp_a2))
        self.assertEqual(response.status_code, 200)
        self.assertIn('responsible', response.context['form'].errors)
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.responsible, self.emp_a)

    def test_cannot_move_to_an_inactive_delegation(self):
        deactivate(Delegation, 'DEL-B')
        self.client.force_login(self.root)
        response = self.client.post(self.url(self.com_a), self.update_payload(
            delegation=self.deleg_b, responsible=self.emp_b))
        self.assertEqual(response.status_code, 200)
        self.assertIn('delegation', response.context['form'].errors)
        self.com_a.refresh_from_db()
        self.assertEqual(self.com_a.delegation, self.deleg_a)

    def test_superuser_can_edit_a_commitment_with_inactive_delegation_and_responsible(self):
        # `com_b` conserva su Delegación B y su responsable, ambos inactivos:
        # es un compromiso antiguo y tiene que poder seguir editándose.
        deactivate(Delegation, 'DEL-B')
        deactivate(Employee, 'EMP-B')
        self.client.force_login(self.root)
        response = self.client.post(self.url(self.com_b), self.payload(
            delegation=self.deleg_b, responsible=self.emp_b,
            origin='Solicitud B', requester='Juan Pérez',
            territory='Sector Norte', observation='Sin cambios de Delegación'))
        self.assertEqual(response.status_code, 302)
        self.com_b.refresh_from_db()
        self.assertEqual(self.com_b.delegation, self.deleg_b)
        self.assertEqual(self.com_b.observation, 'Sin cambios de Delegación')
