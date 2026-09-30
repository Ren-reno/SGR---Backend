"""Pruebas de la eliminación web de Commitment (Fase 6, paso 6.3 / Fase 7,
Decisión 28).

Por HTTP (Client) contra las URLs reales, igual que las de `Activity`
(`tests_activity_delete_web.py`). El token CSRF se prueba con
`Client(enforce_csrf_checks=True)`, porque el Client normal lo salta y no
detectaría un formulario sin token.
Correr con:  python manage.py test performance.tests_commitment_delete_web
"""
import re

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from organization.models import Employee, Position
from performance.models import Commitment
from performance.tests_commitment_web import CommitmentWebTestData, _perms

User = get_user_model()

LIST_URL = reverse('performance:commitment_list')
WARNING = 'Si tiene una validación'  # aviso propio de Evidence: aquí no aplica


def delete_url(commitment):
    return reverse('performance:commitment_delete', args=[commitment.pk])


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


class CommitmentDeleteTestData(CommitmentWebTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        position = Position.objects.get(name='Cargo')
        # Perfil "elimina": como el grupo Administrador del seed, pero SIN ser
        # superuser, para que el scoping por Delegación sí se aplique.
        cls.admin_a = User.objects.create_user('admin_a', password='x')
        _perms(cls.admin_a, 'view_commitment', 'delete_commitment')
        Employee.objects.create(
            institutional_id='ADM-A', user=cls.admin_a, delegation=cls.deleg_a,
            position=position, name='Admin A')


class CommitmentDeleteTests(CommitmentDeleteTestData):
    def assertAlive(self, commitment):
        self.assertTrue(Commitment.objects.filter(pk=commitment.pk).exists())

    # --- Quién puede ---------------------------------------------------

    def test_anonymous_redirects_to_login_and_keeps_commitment(self):
        response = self.client.post(delete_url(self.com_a))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={delete_url(self.com_a)}")
        self.assertAlive(self.com_a)

    def test_user_without_delete_permission_gets_403(self):
        # func_a ve, crea y edita, pero no elimina (como el Funcionario del seed).
        self.client.force_login(self.func_a)
        self.assertEqual(self.client.post(delete_url(self.com_a)).status_code, 403)
        self.assertAlive(self.com_a)

    def test_user_without_any_commitment_permission_gets_403(self):
        # El Verificador del seed no tiene ningún permiso sobre Commitment.
        self.client.force_login(self.verifier)
        self.assertEqual(self.client.post(delete_url(self.com_a)).status_code, 403)
        self.assertAlive(self.com_a)

    def test_user_without_any_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.post(delete_url(self.com_a)).status_code, 403)
        self.assertAlive(self.com_a)

    def test_other_delegation_commitment_is_404(self):
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.post(delete_url(self.com_b)).status_code, 404)
        self.assertAlive(self.com_b)

    def test_superuser_can_delete_in_any_delegation(self):
        self.client.force_login(self.root)
        response = self.client.post(delete_url(self.com_b))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Commitment.objects.filter(pk=self.com_b.pk).exists())

    def test_scope_uses_commitment_delegation_not_current_responsible(self):
        # Igual que el listado y el Admin (Decisión 18): manda
        # `Commitment.delegation`, no la Delegación de quien es responsable hoy.
        mine_led_by_b = Commitment.objects.create(
            delegation=self.deleg_a, responsible=self.emp_b, origin='Mío, lo lleva B',
            requester='x', territory='x', due_date=self.future)
        theirs_led_by_a = Commitment.objects.create(
            delegation=self.deleg_b, responsible=self.emp_a, origin='De B, lo lleva A',
            requester='x', territory='x', due_date=self.future)
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.post(delete_url(theirs_led_by_a)).status_code, 404)
        self.assertAlive(theirs_led_by_a)
        self.assertRedirects(self.client.post(delete_url(mine_led_by_b)), LIST_URL)
        self.assertFalse(Commitment.objects.filter(pk=mine_led_by_b.pk).exists())

    # --- Cómo se pide --------------------------------------------------

    def test_get_is_not_allowed(self):
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.get(delete_url(self.com_a)).status_code, 405)
        self.assertAlive(self.com_a)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_a)
        self.assertEqual(client.post(delete_url(self.com_a)).status_code, 403)
        self.assertAlive(self.com_a)

    def test_token_rendered_in_the_list_page_is_accepted(self):
        # Extremo a extremo: el token que imprime el template es el que el
        # servidor acepta, con la verificación CSRF activa.
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_a)
        html = client.get(LIST_URL).content.decode()
        form = re.search(
            r'<form[^>]+action="%s".*?</form>' % re.escape(delete_url(self.com_a)),
            html, re.S).group(0)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', form).group(1)
        response = client.post(delete_url(self.com_a), {'csrfmiddlewaretoken': token})
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)
        self.assertFalse(Commitment.objects.filter(pk=self.com_a.pk).exists())

    # --- Qué hace ------------------------------------------------------

    def test_delete_is_logical_the_row_stays_in_the_database(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(delete_url(self.com_a), follow=True)
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Commitment.objects.filter(pk=self.com_a.pk).exists())
        row = Commitment.all_objects.get(pk=self.com_a.pk)  # sigue existiendo
        self.assertIsNotNone(row.deleted_at)
        self.assertIn('Compromiso eliminado.', message_texts(response))

    def test_responsible_employee_is_not_touched(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.com_a))
        self.assertTrue(Employee.objects.filter(pk=self.emp_a.pk).exists())

    def test_deleted_commitment_disappears_from_the_list(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.com_a))
        response = self.client.get(LIST_URL)
        self.assertEqual(list(response.context['commitments']), [])

    def test_second_submit_is_404_and_does_not_break(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.com_a))
        self.assertEqual(self.client.post(delete_url(self.com_a)).status_code, 404)

    def test_only_the_targeted_commitment_is_deleted(self):
        other = self._make(self.emp_a2, 'Otro compromiso de A')
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.com_a))
        self.assertAlive(other)


class CommitmentDeleteButtonTests(CommitmentDeleteTestData):
    """Lo que se dibuja en el listado según el permiso."""

    def test_button_and_scripts_only_with_delete_permission(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertContains(response, f'action="{delete_url(self.com_a)}"')
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
        self.assertContains(response, delete_url(self.com_a))
        self.assertNotContains(response, delete_url(self.com_b))

    def test_dialog_does_not_carry_the_evidence_warning(self):
        # El aviso de la validación es de Evidence; un compromiso no tiene hijos.
        self.client.force_login(self.admin_a)
        self.assertNotContains(self.client.get(LIST_URL), WARNING)

    def test_confirmation_text_is_escaped_inside_the_attribute(self):
        # El texto del diálogo incluye datos del registro: no pueden abrir
        # ni cerrar el atributo ni inyectar etiquetas.
        Commitment.objects.filter(pk=self.com_a.pk).update(
            origin='Origen "raro" <b>x</b>')
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertNotContains(response, '<b>x</b>')
        self.assertContains(response, '&quot;raro&quot; &lt;b&gt;x&lt;/b&gt;')
