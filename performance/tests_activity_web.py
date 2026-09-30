"""Pruebas del CRUD web de Activity (Fase 6, paso 6.1).

Se prueba por HTTP (Client), contra las URLs reales, porque los dos errores
de 6.0 (TemplateSyntaxError y el 500 con AnonymousUser) solo aparecieron así.
Correr con:  python manage.py test performance.tests_activity_web
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from organization.models import Delegation, Employee, Position
from performance.forms import ActivityForm
from performance.models import Activity, CatalogItem, Period

User = get_user_model()


def _perms(user, *codenames):
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label='performance', codename=codename)
        )


class ActivityWebTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.deleg_a = Delegation.objects.create(id='DEL-A', name='Delegación A', scope='x')
        cls.deleg_b = Delegation.objects.create(id='DEL-B', name='Delegación B', scope='x')
        position = Position.objects.create(name='Cargo')

        # Funcionario A: mismo perfil de permisos que el grupo Funcionario
        # del seed (ver y editar, no crear).
        cls.func_a = User.objects.create_user('func_a', password='x')
        _perms(cls.func_a, 'view_activity', 'change_activity')
        # Sin ningún permiso de modelo (como el grupo Delegado hoy).
        cls.sin_permiso = User.objects.create_user('sin_permiso', password='x')
        cls.root = User.objects.create_superuser('root', 'r@x.cl', 'x')
        user_b = User.objects.create_user('func_b', password='x')

        cls.emp_a = Employee.objects.create(
            institutional_id='EMP-A', user=cls.func_a, delegation=cls.deleg_a,
            position=position, name='Empleado A')
        cls.emp_b = Employee.objects.create(
            institutional_id='EMP-B', user=user_b, delegation=cls.deleg_b,
            position=position, name='Empleado B')

        cls.period = Period.objects.create(
            start_date='2026-01-01', end_date='2026-12-31', computable_days=200,
            status='abierto', amber_threshold='70.00', collective_threshold='90.00')
        cls.attention, _ = CatalogItem.objects.get_or_create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Atención test')

        cls.act_a = cls._make(cls.emp_a, 'solicitud A')
        cls.act_b = cls._make(cls.emp_b, 'solicitud B')

    @classmethod
    def _make(cls, employee, description, date='2026-06-01'):
        return Activity.objects.create(
            employee=employee, period=cls.period, attention=cls.attention,
            activity_type='Primera Atención', service='s', sub_attention='sa',
            date=date, request_description=description, action_taken='a',
            status='Pendiente')

    def payload(self, employee=None, **overrides):
        data = {
            'employee': (employee or self.emp_a).pk,
            'period': self.period.pk,
            'meta': '',
            'activity_type': 'Seguimiento',
            'service': 'Atención Presencial',
            'attention': self.attention.pk,
            'sub_attention': 'Orientación Social',
            'date': '2026-07-10',
            'request_description': 'Consulta nueva',
            'action_taken': 'Se orientó',
            'contact_name': '',
            'contact_phone': '',
            'status': 'Pendiente',
        }
        data.update(overrides)
        return data


class ActivityListTests(ActivityWebTestData):
    url = reverse('performance:activity_list')

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_user_without_view_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_user_sees_only_own_delegation(self):
        self.client.force_login(self.func_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['activities']), [self.act_a])
        self.assertNotContains(response, 'Empleado B')

    def test_superuser_sees_all(self):
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertCountEqual(response.context['activities'], [self.act_a, self.act_b])

    def test_soft_deleted_activity_is_not_listed(self):
        self.act_a.soft_delete()
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['activities']), [self.act_b])

    def test_add_button_only_with_add_permission(self):
        create_url = reverse('performance:activity_create')
        self.client.force_login(self.func_a)
        self.assertNotContains(self.client.get(self.url), create_url)
        self.client.force_login(self.root)
        self.assertContains(self.client.get(self.url), create_url)

    def test_paginates_with_page_size_from_url(self):
        for i in range(7):
            self._make(self.emp_a, f'extra {i}', date=f'2026-02-{i + 1:02d}')
        self.client.force_login(self.func_a)
        response = self.client.get(self.url, {'per_page': 5})
        self.assertEqual(len(response.context['activities']), 5)
        self.assertTrue(response.context['page_obj'].has_next())
        page2 = self.client.get(self.url, {'page': 2})  # el tamaño quedó en sesión
        self.assertEqual(len(page2.context['activities']), 3)


class ActivityCreateTests(ActivityWebTestData):
    url = reverse('performance:activity_create')

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_user_without_add_permission_gets_403(self):
        self.client.force_login(self.func_a)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        before = Activity.objects.count()
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)
        self.assertEqual(Activity.objects.count(), before)

    def test_superuser_creates_activity(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse('performance:activity_list'))
        self.assertTrue(Activity.objects.filter(request_description='Consulta nueva').exists())

    def test_date_outside_period_is_rejected(self):
        self.client.force_login(self.root)
        before = Activity.objects.count()
        response = self.client.post(self.url, self.payload(date='2027-03-01'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('date', response.context['form'].errors)
        self.assertEqual(Activity.objects.count(), before)

    def test_required_fields_are_enforced(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload(
            request_description='   ', action_taken='', activity_type=''))
        errors = response.context['form'].errors
        for field in ('request_description', 'action_taken', 'activity_type'):
            self.assertIn(field, errors)

    def test_duplicate_is_rejected(self):
        self.client.force_login(self.root)
        dup = self.payload(
            date='2026-06-01', activity_type='Primera Atención',
            request_description='SOLICITUD a')  # igual a act_a salvo mayúsculas
        before = Activity.objects.count()
        response = self.client.post(self.url, dup)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertEqual(Activity.objects.count(), before)

    def test_duplicate_check_ignores_soft_deleted(self):
        self.act_a.soft_delete()
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload(
            date='2026-06-01', activity_type='Primera Atención',
            request_description='solicitud A'))
        self.assertEqual(response.status_code, 302)

    def test_invalid_phone_is_rejected_and_valid_one_accepted(self):
        self.client.force_login(self.root)
        bad = self.client.post(self.url, self.payload(contact_phone='abc'))
        self.assertIn('contact_phone', bad.context['form'].errors)
        ok = self.client.post(self.url, self.payload(contact_phone='+56 9 1234 5678'))
        self.assertEqual(ok.status_code, 302)


class ActivityUpdateTests(ActivityWebTestData):
    def url(self, activity):
        return reverse('performance:activity_update', args=[activity.pk])

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url(self.act_a))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={self.url(self.act_a)}")

    def test_user_without_change_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.get(self.url(self.act_a)).status_code, 403)

    def test_edits_own_delegation_activity(self):
        self.client.force_login(self.func_a)
        response = self.client.post(
            self.url(self.act_a), self.payload(date='2026-06-01',
                                              request_description='editada'))
        self.assertRedirects(response, reverse('performance:activity_list'))
        self.act_a.refresh_from_db()
        self.assertEqual(self.act_a.request_description, 'editada')

    def test_form_prefilled_with_current_values(self):
        self.client.force_login(self.func_a)
        response = self.client.get(self.url(self.act_a))
        self.assertContains(response, 'value="2026-06-01"')

    def test_other_delegation_activity_is_404(self):
        self.client.force_login(self.func_a)
        self.assertEqual(self.client.get(self.url(self.act_b)).status_code, 404)
        response = self.client.post(self.url(self.act_b), self.payload(employee=self.emp_b))
        self.assertEqual(response.status_code, 404)
        self.act_b.refresh_from_db()
        self.assertEqual(self.act_b.request_description, 'solicitud B')

    def test_cannot_reassign_to_employee_of_other_delegation(self):
        # El bypass que el scoping de la vista, por sí solo, no cierra.
        self.client.force_login(self.func_a)
        response = self.client.post(
            self.url(self.act_a), self.payload(employee=self.emp_b, date='2026-06-01'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('employee', response.context['form'].errors)
        self.act_a.refresh_from_db()
        self.assertEqual(self.act_a.employee, self.emp_a)

    def test_saving_without_changes_is_not_a_duplicate_of_itself(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.act_a), self.payload(
            date='2026-06-01', activity_type='Primera Atención',
            request_description='solicitud A'))
        self.assertEqual(response.status_code, 302)

    def test_soft_deleted_activity_is_404(self):
        self.act_a.soft_delete()
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.url(self.act_a)).status_code, 404)


class ActivityFormScopingTests(ActivityWebTestData):
    def test_employee_choices_limited_to_own_delegation(self):
        form = ActivityForm(user=self.func_a)
        self.assertEqual(list(form.fields['employee'].queryset), [self.emp_a])

    def test_superuser_gets_all_employees(self):
        form = ActivityForm(user=self.root)
        self.assertCountEqual(form.fields['employee'].queryset, [self.emp_a, self.emp_b])

    def test_inactive_catalog_item_hidden_unless_already_selected(self):
        old = CatalogItem.objects.create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Antigua', is_active=False)
        self.assertNotIn(old, ActivityForm(user=self.root).fields['attention'].queryset)
        self.act_a.attention = old
        self.act_a.save()
        editing = ActivityForm(instance=self.act_a, user=self.root)
        self.assertIn(old, editing.fields['attention'].queryset)
