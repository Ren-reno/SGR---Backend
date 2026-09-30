"""Pruebas de la eliminación web de Activity (Fase 7, Decisión 26).

Por HTTP (Client) contra las URLs reales, igual que las de 6.1. El token CSRF
se prueba con `Client(enforce_csrf_checks=True)`, porque el Client normal lo
salta y no detectaría un formulario sin token.
Correr con:  python manage.py test performance.tests_activity_delete_web
"""
import re
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.staticfiles import finders
from django.test import Client
from django.urls import reverse

from organization.models import Employee, Position
from performance.models import Activity, Evidence
from performance.tests_activity_web import ActivityWebTestData, _perms

User = get_user_model()

LIST_URL = reverse('performance:activity_list')


def delete_url(activity):
    return reverse('performance:activity_delete', args=[activity.pk])


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


class ActivityDeleteTestData(ActivityWebTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        position = Position.objects.get(name='Cargo')
        # Perfil "elimina": como el grupo Administrador del seed, pero SIN ser
        # superuser, para que el scoping por Delegación sí se aplique.
        cls.admin_a = User.objects.create_user('admin_a', password='x')
        _perms(cls.admin_a, 'view_activity', 'delete_activity')
        Employee.objects.create(
            institutional_id='ADM-A', user=cls.admin_a, delegation=cls.deleg_a,
            position=position, name='Admin A')


class ActivityDeleteTests(ActivityDeleteTestData):
    def assertAlive(self, activity):
        self.assertTrue(Activity.objects.filter(pk=activity.pk).exists())

    # --- Quién puede ---------------------------------------------------

    def test_anonymous_redirects_to_login_and_keeps_activity(self):
        response = self.client.post(delete_url(self.act_a))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={delete_url(self.act_a)}")
        self.assertAlive(self.act_a)

    def test_user_without_delete_permission_gets_403(self):
        # func_a puede ver y editar, pero no eliminar (como el Funcionario del seed).
        self.client.force_login(self.func_a)
        self.assertEqual(self.client.post(delete_url(self.act_a)).status_code, 403)
        self.assertAlive(self.act_a)

    def test_user_without_any_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.post(delete_url(self.act_a)).status_code, 403)
        self.assertAlive(self.act_a)

    def test_other_delegation_activity_is_404(self):
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.post(delete_url(self.act_b)).status_code, 404)
        self.assertAlive(self.act_b)

    def test_superuser_can_delete_in_any_delegation(self):
        self.client.force_login(self.root)
        response = self.client.post(delete_url(self.act_b))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Activity.objects.filter(pk=self.act_b.pk).exists())

    # --- Cómo se pide --------------------------------------------------

    def test_get_is_not_allowed(self):
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.get(delete_url(self.act_a)).status_code, 405)
        self.assertAlive(self.act_a)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_a)
        self.assertEqual(client.post(delete_url(self.act_a)).status_code, 403)
        self.assertAlive(self.act_a)

    def test_token_rendered_in_the_list_page_is_accepted(self):
        # Extremo a extremo: el token que imprime el template es el que el
        # servidor acepta, con la verificación CSRF activa.
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_a)
        html = client.get(LIST_URL).content.decode()
        form = re.search(
            r'<form[^>]+action="%s".*?</form>' % re.escape(delete_url(self.act_a)),
            html, re.S).group(0)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', form).group(1)
        response = client.post(delete_url(self.act_a), {'csrfmiddlewaretoken': token})
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)
        self.assertFalse(Activity.objects.filter(pk=self.act_a.pk).exists())

    # --- Qué hace ------------------------------------------------------

    def test_delete_is_logical_the_row_stays_in_the_database(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(delete_url(self.act_a), follow=True)
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Activity.objects.filter(pk=self.act_a.pk).exists())
        row = Activity.all_objects.get(pk=self.act_a.pk)  # sigue existiendo
        self.assertIsNotNone(row.deleted_at)
        self.assertIn('Actividad eliminada.', message_texts(response))

    def test_deleted_activity_disappears_from_the_list(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.act_a))
        response = self.client.get(LIST_URL)
        self.assertEqual(list(response.context['activities']), [])

    def test_second_submit_is_404_and_does_not_break(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.act_a))
        self.assertEqual(self.client.post(delete_url(self.act_a)).status_code, 404)

    def test_activity_with_live_evidence_is_protected_not_a_500(self):
        evidence = Evidence.objects.create(
            code='EV-DEL', activity=self.act_a, file='x/a.pdf', date=date(2026, 6, 2))
        self.client.force_login(self.admin_a)
        response = self.client.post(delete_url(self.act_a), follow=True)
        self.assertRedirects(response, LIST_URL)
        self.assertAlive(self.act_a)
        self.assertTrue(any('evidencias' in m for m in message_texts(response)))
        # Con la evidencia ya eliminada, sí se puede.
        evidence.soft_delete()
        self.client.post(delete_url(self.act_a))
        self.assertFalse(Activity.objects.filter(pk=self.act_a.pk).exists())


class ActivityDeleteButtonTests(ActivityDeleteTestData):
    """Lo que se dibuja en el listado según el permiso."""

    def test_button_and_scripts_only_with_delete_permission(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertContains(response, f'action="{delete_url(self.act_a)}"')
        self.assertContains(response, 'js-confirm-delete')
        self.assertContains(response, '/static/performance/vendor/sweetalert2/sweetalert2.all.min.js')
        self.assertContains(response, '/static/performance/js/confirm-delete.js')
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_no_button_and_no_scripts_without_delete_permission(self):
        self.client.force_login(self.func_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'js-confirm-delete')
        self.assertNotContains(response, 'sweetalert2')
        self.assertNotContains(response, '/delete/')

    def test_only_rows_of_own_delegation_get_a_button(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertContains(response, delete_url(self.act_a))
        self.assertNotContains(response, delete_url(self.act_b))

    def test_confirmation_text_is_escaped_inside_the_attribute(self):
        # El texto del diálogo incluye datos del registro: no pueden abrir
        # ni cerrar el atributo ni inyectar etiquetas.
        Activity.objects.filter(pk=self.act_a.pk).update(
            activity_type='Tipo "raro" <b>x</b>')
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertNotContains(response, '<b>x</b>')
        self.assertContains(response, '&quot;raro&quot; &lt;b&gt;x&lt;/b&gt;')


class VendoredAssetsTests(ActivityDeleteTestData):
    def test_static_files_are_shipped_with_the_app(self):
        # Si alguien los saca del repo (o un .gitignore los excluye), el
        # botón dejaría de funcionar sin ningún error visible en el servidor.
        for path in (
            'performance/vendor/sweetalert2/sweetalert2.all.min.js',
            'performance/vendor/sweetalert2/LICENSE',
            'performance/js/confirm-delete.js',
        ):
            self.assertIsNotNone(finders.find(path), path)
