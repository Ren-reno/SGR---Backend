"""Pruebas de la portada `/`, del destino tras el login y de la zona horaria
(Fase 6, patch 13, Decisión 27).

Se prueba por HTTP (Client), contra las URLs reales. Los perfiles de cada rol
salen de `PERMISOS_POR_GRUPO` del seed y no de una copia escrita a mano: si el
seed cambia lo que puede ver un rol, estos tests lo detectan.
Correr con:  python manage.py test performance.tests_home_web
"""
from datetime import date, datetime, timezone as dt_timezone
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from performance.management.commands.seed_sgr import PERMISOS_POR_GRUPO
from performance.models import Commitment
from performance.tests_commitment_web import CommitmentWebTestData

User = get_user_model()

HOME_URL = reverse('performance:home')

# nombre corto -> nombre de la ruta del listado. Es lo que la portada enlaza.
MODULES = {
    'activity': 'performance:activity_list',
    'evidence': 'performance:evidence_list',
    'validation': 'performance:validation_list',
    'commitment': 'performance:commitment_list',
}
EMPTY_STATE_TEXT = 'ningún módulo'


def make_user(username, *, group=None, codenames=(), is_staff=False):
    """Usuario con los permisos del grupo del seed (`group`) o con solo los
    `view_*` indicados. Nunca es superuser: así el scoping y los permisos
    sí se aplican."""
    user = User.objects.create_user(username, password='x', is_staff=is_staff)
    if group is not None:
        grp = Group.objects.create(name=group)
        # "Delegado" no está en PERMISOS_POR_GRUPO: existe, pero sin permisos.
        for app_label, codename in PERMISOS_POR_GRUPO.get(group, []):
            grp.permissions.add(Permission.objects.get(
                content_type__app_label=app_label, codename=codename))
        user.groups.add(grp)
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(
            content_type__app_label='performance', codename=codename))
    return user


def linked_modules(response):
    """Conjunto de módulos cuyo enlace aparece en la portada."""
    return {
        name for name, url_name in MODULES.items()
        if f'href="{reverse(url_name)}"' in response.content.decode()
    }


class HomeAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user('ana', group='Funcionario')

    def test_home_is_the_site_root(self):
        self.assertEqual(HOME_URL, '/')

    def test_anonymous_redirects_to_login_with_next(self):
        response = self.client.get(HOME_URL)
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next=/")

    def test_authenticated_user_gets_the_home_page(self):
        self.client.force_login(self.user)
        response = self.client.get(HOME_URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'performance/home.html')

    def test_login_lands_on_home(self):
        # Extremo a extremo: entra por el formulario real y sigue el redirect.
        response = self.client.post(
            reverse('accounts:login'), {'username': 'ana', 'password': 'x'},
            follow=True)
        self.assertEqual(response.redirect_chain, [(HOME_URL, 302)])
        self.assertTemplateUsed(response, 'performance/home.html')

    def test_login_still_honours_next(self):
        response = self.client.post(
            reverse('accounts:login') + '?next=/admin/',
            {'username': 'ana', 'password': 'x', 'next': '/admin/'})
        self.assertRedirects(response, '/admin/', fetch_redirect_response=False)

    def test_logged_in_user_visiting_login_is_sent_home(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:login'))
        self.assertRedirects(response, HOME_URL)


class HomeLinksByRoleTests(TestCase):
    """Cada rol ve solo los enlaces de los listados que puede abrir."""

    def links_for(self, user):
        self.client.force_login(user)
        response = self.client.get(HOME_URL)
        self.assertEqual(response.status_code, 200)
        return response

    def test_administrador_sees_all_four(self):
        response = self.links_for(make_user('adm', group='Administrador'))
        self.assertEqual(linked_modules(response), set(MODULES))
        self.assertNotContains(response, EMPTY_STATE_TEXT)

    def test_funcionario_sees_activity_evidence_and_commitment(self):
        response = self.links_for(make_user('func', group='Funcionario'))
        self.assertEqual(
            linked_modules(response), {'activity', 'evidence', 'commitment'})
        self.assertNotContains(response, EMPTY_STATE_TEXT)

    def test_verificador_sees_activity_evidence_and_validation(self):
        response = self.links_for(make_user('verif', group='Verificador'))
        self.assertEqual(
            linked_modules(response), {'activity', 'evidence', 'validation'})
        self.assertNotContains(response, EMPTY_STATE_TEXT)

    def test_delegado_without_permissions_sees_the_empty_state(self):
        response = self.links_for(make_user('deleg', group='Delegado'))
        self.assertEqual(linked_modules(response), set())
        self.assertContains(response, EMPTY_STATE_TEXT)

    def test_user_with_no_group_sees_the_empty_state(self):
        response = self.links_for(make_user('nadie'))
        self.assertEqual(linked_modules(response), set())
        self.assertContains(response, EMPTY_STATE_TEXT)

    def test_each_link_depends_only_on_its_own_view_permission(self):
        # Un usuario con UN solo permiso `view_*` ve exactamente ese enlace.
        # Es lo que detecta que a un enlace le falte su condición `perms.*`.
        for name in MODULES:
            with self.subTest(module=name):
                user = make_user(f'solo_{name}', codenames=[f'view_{name}'])
                response = self.links_for(user)
                self.assertEqual(linked_modules(response), {name})
                self.assertNotContains(response, EMPTY_STATE_TEXT)

    def test_add_change_delete_permissions_do_not_show_a_link(self):
        # El enlace es al listado: sin `view_*` no hay enlace, aunque la
        # persona pueda crear, editar o eliminar.
        user = make_user('sin_view', codenames=[
            'add_activity', 'change_activity', 'delete_activity'])
        response = self.links_for(user)
        self.assertEqual(linked_modules(response), set())
        self.assertContains(response, EMPTY_STATE_TEXT)

    def test_superuser_without_employee_sees_all_four(self):
        root = User.objects.create_superuser('root', 'r@x.cl', 'x')
        response = self.links_for(root)
        self.assertEqual(linked_modules(response), set(MODULES))


class HomeAdminLinkTests(TestCase):
    admin_href = f'href="{reverse("admin:index")}"'

    def test_staff_sees_the_admin_link(self):
        self.client.force_login(make_user('st', group='Funcionario', is_staff=True))
        self.assertContains(self.client.get(HOME_URL), self.admin_href)

    def test_non_staff_does_not_see_the_admin_link(self):
        self.client.force_login(make_user('ns', group='Funcionario'))
        self.assertNotContains(self.client.get(HOME_URL), self.admin_href)

    def test_admin_link_is_independent_of_module_permissions(self):
        # Staff sin ningún permiso: ve el estado vacío Y el enlace al Admin.
        self.client.force_login(make_user('st_vacio', is_staff=True))
        response = self.client.get(HOME_URL)
        self.assertContains(response, EMPTY_STATE_TEXT)
        self.assertContains(response, self.admin_href)


class TimeZoneTests(TestCase):
    """TIME_ZONE = 'America/Santiago' (Decisión 27, punto 5)."""

    def test_setting_is_chile(self):
        self.assertEqual(settings.TIME_ZONE, 'America/Santiago')

    def test_localdate_is_chilean_in_summer(self):
        # 16-ene-2026 02:30 UTC = 15-ene 23:30 en Santiago (UTC-3, verano).
        now = datetime(2026, 1, 16, 2, 30, tzinfo=dt_timezone.utc)
        with mock.patch('django.utils.timezone.now', return_value=now):
            self.assertEqual(timezone.localdate(), date(2026, 1, 15))

    def test_localdate_is_chilean_in_winter(self):
        # 16-jul-2026 01:30 UTC = 15-jul 21:30 en Santiago (UTC-4, invierno).
        now = datetime(2026, 7, 16, 1, 30, tzinfo=dt_timezone.utc)
        with mock.patch('django.utils.timezone.now', return_value=now):
            self.assertEqual(timezone.localdate(), date(2026, 7, 15))


class CommitmentDueDateLateAtNightTests(CommitmentWebTestData):
    """Regresión del bug que motivó el cambio: de noche en Chile, elegir
    "hoy" como fecha comprometida se rechazaba porque el servidor ya estaba
    en "mañana" (UTC)."""
    url = reverse('performance:commitment_create')
    # 15-ene-2026 23:30 en Santiago = 16-ene 02:30 UTC.
    late_night = datetime(2026, 1, 16, 2, 30, tzinfo=dt_timezone.utc)

    def post_at_late_night(self, due_date):
        self.client.force_login(self.func_a)
        with mock.patch('django.utils.timezone.now', return_value=self.late_night):
            return self.client.post(self.url, self.payload(due_date=due_date))

    def test_chilean_today_is_accepted(self):
        response = self.post_at_late_night('2026-01-15')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Commitment.objects.filter(
            requester='María Soto', due_date=date(2026, 1, 15)).exists())

    def test_chilean_yesterday_is_still_rejected(self):
        response = self.post_at_late_night('2026-01-14')
        self.assertEqual(response.status_code, 200)
        self.assertIn('due_date', response.context['form'].errors)
