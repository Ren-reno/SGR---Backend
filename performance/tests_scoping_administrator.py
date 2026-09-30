"""Pruebas del alcance del scoping del grupo Administrador (patch 17, Decisión 31).

Hasta este patch el scoping web solo eximía al superuser, mientras que el Admin
(`_unrestricted`) eximía también al grupo `Administrador`. Ahora las dos capas
usan la misma función, `performance.scoping.is_unrestricted`.

Se prueba un criterio a la vez (superuser, grupo Administrador, usuario normal,
anónimo), y después cada superficie que depende de él: las funciones de
scoping, las cuatro listas web, los desplegables de los formularios y el
acuerdo con el Admin.

Correr con:  python manage.py test performance.tests_scoping_administrator
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse

from organization.models import Delegation, Employee, Position
from performance.admin import _unrestricted
from performance.forms import (
    ActivityForm, CommitmentForm, EvidenceForm, ValidationForm,
)
from performance.models import Activity, CatalogItem, Commitment, Evidence, Period, Validation
from performance.scoping import (
    is_unrestricted, scope_delegations_for_user, scope_queryset_for_user,
)

User = get_user_model()

LISTS = ('activity_list', 'evidence_list', 'validation_list', 'commitment_list')
VIEW_PERMS = ('view_activity', 'view_evidence', 'view_validation', 'view_commitment')


def _perms(user, *codenames):
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(
            content_type__app_label='performance', codename=codename))


class ScopingAdministratorData(TestCase):
    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name='Administrador')
        verifier_group = Group.objects.create(name='Verificador')
        cls.func_group = Group.objects.create(name='Funcionario')

        cls.deleg_a = Delegation.objects.create(id='DEL-A', name='Delegación A', scope='x')
        cls.deleg_b = Delegation.objects.create(id='DEL-B', name='Delegación B', scope='x')
        position = Position.objects.create(name='Cargo')

        def make(username, *, group=None, superuser=False, delegation=None):
            user = User.objects.create_user(username, password='x', is_superuser=superuser)
            _perms(user, *VIEW_PERMS)
            if group is not None:
                user.groups.add(group)
            employee = None
            if delegation is not None:
                employee = Employee.objects.create(
                    institutional_id=f'EMP-{username}', user=user,
                    delegation=delegation, position=position, name=username)
            return user, employee

        cls.root, _ = make('root', superuser=True)
        # Administrador SIN ser superuser, con Employee en la Delegación A.
        cls.admin_a, _ = make('admin_a', group=admin_group, delegation=cls.deleg_a)
        # Administrador sin Employee (caso borde de la Decisión 6).
        cls.admin_bare, _ = make('admin_bare', group=admin_group)
        # Usuarios normales: acotados a su Delegación.
        cls.func_a, cls.emp_func_a = make('func_a', group=cls.func_group, delegation=cls.deleg_a)
        cls.verif_a, cls.emp_verif_a = make('verif_a', group=verifier_group, delegation=cls.deleg_a)
        cls.func_b, cls.emp_func_b = make('func_b', delegation=cls.deleg_b)
        cls.verif_b, cls.emp_verif_b = make('verif_b', group=verifier_group, delegation=cls.deleg_b)
        # Usuario normal sin Employee: no ve nada.
        cls.bare, _ = make('bare')

        cls.period = Period.objects.create(
            start_date='2026-01-01', end_date='2026-12-31', computable_days=200,
            status='abierto', amber_threshold='70.00', collective_threshold='90.00')
        cls.attention, _ = CatalogItem.objects.get_or_create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Atención')

        def make_activity(employee, tag):
            return Activity.objects.create(
                employee=employee, period=cls.period, activity_type='Tipo',
                service='Servicio', attention=cls.attention, sub_attention='Sub',
                date='2026-06-01', request_description=f'Solicitud {tag}',
                action_taken='Acción', status='ingresado')

        cls.act_a = make_activity(cls.emp_func_a, 'A')
        cls.act_b = make_activity(cls.emp_func_b, 'B')
        cls.ev_a = Evidence.objects.create(
            code='EV-A', activity=cls.act_a, file='evidence/x.pdf', date='2026-06-02')
        cls.ev_b = Evidence.objects.create(
            code='EV-B', activity=cls.act_b, file='evidence/x.pdf', date='2026-06-02')
        cls.val_a = Validation.objects.create(
            evidence=cls.ev_a, employee=cls.emp_verif_a, decision='Aprobada',
            date='2026-06-03', result=True)
        cls.val_b = Validation.objects.create(
            evidence=cls.ev_b, employee=cls.emp_verif_b, decision='Aprobada',
            date='2026-06-03', result=True)
        cls.com_a = Commitment.objects.create(
            delegation=cls.deleg_a, responsible=cls.emp_func_a, origin='Origen A',
            requester='Solicitante', territory='Territorio', due_date='2099-01-01')
        cls.com_b = Commitment.objects.create(
            delegation=cls.deleg_b, responsible=cls.emp_func_b, origin='Origen B',
            requester='Solicitante', territory='Territorio', due_date='2099-01-01')


class IsUnrestrictedTests(ScopingAdministratorData):
    """Un test por criterio: es la definición única de la regla."""

    def test_superuser_is_unrestricted(self):
        self.assertTrue(is_unrestricted(self.root))

    def test_administrator_group_is_unrestricted_without_being_superuser(self):
        self.assertFalse(self.admin_a.is_superuser)
        self.assertTrue(is_unrestricted(self.admin_a))

    def test_administrator_group_does_not_need_an_employee(self):
        self.assertFalse(hasattr(self.admin_bare, 'employee'))
        self.assertTrue(is_unrestricted(self.admin_bare))

    def test_normal_user_is_restricted(self):
        self.assertFalse(is_unrestricted(self.func_a))

    def test_other_groups_do_not_unlock_the_scoping(self):
        # El Verificador tiene un rol propio (revisar), no alcance total.
        self.assertFalse(is_unrestricted(self.verif_a))
        self.assertFalse(is_unrestricted(self.func_a))

    def test_user_without_group_or_employee_is_restricted(self):
        self.assertFalse(is_unrestricted(self.bare))

    def test_anonymous_is_restricted(self):
        self.assertFalse(is_unrestricted(AnonymousUser()))

    def test_staff_flag_alone_does_not_unlock_the_scoping(self):
        User.objects.filter(pk=self.func_a.pk).update(is_staff=True)
        self.assertFalse(is_unrestricted(User.objects.get(pk=self.func_a.pk)))


class ScopingFunctionsTests(ScopingAdministratorData):
    def codes(self, user):
        return set(scope_queryset_for_user(
            Evidence.objects.all(), user, 'activity__employee__'
        ).values_list('code', flat=True))

    def test_superuser_sees_every_delegation(self):
        self.assertEqual(self.codes(self.root), {'EV-A', 'EV-B'})

    def test_administrator_group_sees_every_delegation(self):
        self.assertEqual(self.codes(self.admin_a), {'EV-A', 'EV-B'})

    def test_administrator_group_without_employee_sees_everything_and_does_not_crash(self):
        self.assertEqual(self.codes(self.admin_bare), {'EV-A', 'EV-B'})

    def test_normal_user_sees_only_their_delegation(self):
        self.assertEqual(self.codes(self.func_a), {'EV-A'})
        self.assertEqual(self.codes(self.func_b), {'EV-B'})

    def test_normal_user_without_employee_sees_nothing(self):
        self.assertEqual(self.codes(self.bare), set())

    def test_anonymous_sees_nothing(self):
        self.assertEqual(self.codes(AnonymousUser()), set())

    def test_delegations_scope_follows_the_same_rule(self):
        def ids(user):
            return set(scope_delegations_for_user(
                Delegation.objects.all(), user).values_list('id', flat=True))
        self.assertEqual(ids(self.root), {'DEL-A', 'DEL-B'})
        self.assertEqual(ids(self.admin_a), {'DEL-A', 'DEL-B'})
        self.assertEqual(ids(self.admin_bare), {'DEL-A', 'DEL-B'})
        self.assertEqual(ids(self.func_a), {'DEL-A'})
        self.assertEqual(ids(self.bare), set())
        self.assertEqual(ids(AnonymousUser()), set())


class ScopingWebListsTests(ScopingAdministratorData):
    """Las cuatro listas web, con un usuario por criterio."""

    def rows(self, user, name):
        self.client.force_login(user)
        response = self.client.get(reverse(f'performance:{name}'))
        self.assertEqual(response.status_code, 200)
        return list(response.context['object_list'])

    def test_administrator_group_sees_both_delegations_in_all_four_lists(self):
        for name in LISTS:
            with self.subTest(list=name):
                self.assertEqual(len(self.rows(self.admin_a, name)), 2)

    def test_administrator_group_without_employee_gets_the_full_lists_not_an_empty_page(self):
        for name in LISTS:
            with self.subTest(list=name):
                self.assertEqual(len(self.rows(self.admin_bare, name)), 2)

    def test_superuser_sees_both_delegations_in_all_four_lists(self):
        for name in LISTS:
            with self.subTest(list=name):
                self.assertEqual(len(self.rows(self.root, name)), 2)

    def test_normal_user_sees_only_their_delegation_in_all_four_lists(self):
        # verif_a tiene los 4 permisos `view_*` de este archivo.
        for name in LISTS:
            with self.subTest(list=name):
                self.assertEqual(len(self.rows(self.verif_a, name)), 1)

    def test_normal_user_without_employee_gets_an_empty_list_not_a_500(self):
        for name in LISTS:
            with self.subTest(list=name):
                self.assertEqual(self.rows(self.bare, name), [])


class ScopingFormDropdownsTests(ScopingAdministratorData):
    """Los desplegables de FK usan el mismo criterio que las listas."""

    def test_activity_form_offers_every_employee_to_an_administrator_group_user(self):
        form = ActivityForm(user=self.admin_a)
        offered = set(form.fields['employee'].queryset.values_list('pk', flat=True))
        self.assertLessEqual({self.emp_func_a.pk, self.emp_func_b.pk}, offered)

    def test_activity_form_offers_only_own_delegation_to_a_normal_user(self):
        form = ActivityForm(user=self.func_a)
        offered = set(form.fields['employee'].queryset.values_list('pk', flat=True))
        self.assertIn(self.emp_func_a.pk, offered)
        self.assertNotIn(self.emp_func_b.pk, offered)

    def test_evidence_form_offers_every_activity_to_an_administrator_group_user(self):
        form = EvidenceForm(user=self.admin_a)
        offered = set(form.fields['activity'].queryset.values_list('pk', flat=True))
        self.assertEqual(offered, {self.act_a.pk, self.act_b.pk})

    def test_evidence_form_offers_only_own_activities_to_a_normal_user(self):
        form = EvidenceForm(user=self.func_a)
        offered = set(form.fields['activity'].queryset.values_list('pk', flat=True))
        self.assertEqual(offered, {self.act_a.pk})

    def test_validation_form_offers_every_verifier_to_an_administrator_group_user(self):
        form = ValidationForm(user=self.admin_a)
        offered = set(form.fields['employee'].queryset.values_list('pk', flat=True))
        self.assertEqual(offered, {self.emp_verif_a.pk, self.emp_verif_b.pk})

    def test_validation_form_offers_only_own_verifiers_to_a_normal_user(self):
        form = ValidationForm(user=self.verif_a)
        offered = set(form.fields['employee'].queryset.values_list('pk', flat=True))
        self.assertEqual(offered, {self.emp_verif_a.pk})

    def test_commitment_form_offers_every_delegation_and_no_preselection_to_an_administrator_group_user(self):
        form = CommitmentForm(user=self.admin_a)
        offered = set(form.fields['delegation'].queryset.values_list('pk', flat=True))
        self.assertEqual(offered, {'DEL-A', 'DEL-B'})
        self.assertIsNone(form.initial.get('delegation'))

    def test_commitment_form_preselects_the_only_delegation_of_a_normal_user(self):
        form = CommitmentForm(user=self.func_a)
        offered = set(form.fields['delegation'].queryset.values_list('pk', flat=True))
        self.assertEqual(offered, {'DEL-A'})
        self.assertEqual(form.initial.get('delegation'), 'DEL-A')

    def test_a_normal_user_cannot_post_an_activity_of_another_delegation(self):
        # El desplegable acotado es lo que impide el POST cruzado.
        form = ActivityForm(user=self.func_a)
        self.assertNotIn(self.emp_func_b.pk, [
            pk for pk, _ in form.fields['employee'].choices if pk != ''])


class ScopingAgreesWithAdminTests(ScopingAdministratorData):
    """Web y Admin comparten la definición: no pueden volver a divergir."""

    def test_admin_and_web_agree_for_every_kind_of_user(self):
        factory = RequestFactory()
        for label, user in [
            ('superuser', self.root), ('administrador', self.admin_a),
            ('administrador sin employee', self.admin_bare),
            ('funcionario', self.func_a), ('verificador', self.verif_a),
            ('sin employee', self.bare), ('anónimo', AnonymousUser()),
        ]:
            with self.subTest(user=label):
                request = factory.get('/')
                request.user = user
                self.assertEqual(_unrestricted(request), is_unrestricted(user))

    def test_admin_still_treats_the_administrator_group_as_unrestricted(self):
        request = RequestFactory().get('/')
        request.user = self.admin_a
        self.assertTrue(_unrestricted(request))
