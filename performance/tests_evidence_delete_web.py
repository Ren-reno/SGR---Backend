"""Pruebas de la eliminación web de Evidence (Fase 6, paso 6.3 / Fase 7,
Decisión 28).

Por HTTP (Client) contra las URLs reales, igual que las de `Activity`
(`tests_activity_delete_web.py`). El token CSRF se prueba con
`Client(enforce_csrf_checks=True)`, porque el Client normal lo salta y no
detectaría un formulario sin token.
Correr con:  python manage.py test performance.tests_evidence_delete_web
"""
import re

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import connection
from django.template import engines
from django.template.loader import render_to_string
from django.test import Client, SimpleTestCase, RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from organization.models import Employee, Position
from performance.models import Activity, Evidence, Validation
from performance.tests_evidence_web import EvidenceWebTestData, _TEST_MEDIA, _perms

User = get_user_model()

LIST_URL = reverse('performance:evidence_list')
ACTIVITY_LIST_URL = reverse('performance:activity_list')
WARNING = 'Si tiene una validación, también se eliminará.'


def delete_url(evidence):
    return reverse('performance:evidence_delete', args=[evidence.pk])


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class EvidenceDeleteTestData(EvidenceWebTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        position = Position.objects.get(name='Cargo')
        # Perfil "elimina": como el grupo Administrador del seed, pero SIN ser
        # superuser, para que el scoping por Delegación sí se aplique. Puede
        # ver y eliminar evidencias, actividades y validaciones.
        cls.admin_a = User.objects.create_user('admin_a', password='x')
        _perms(cls.admin_a, 'view_evidence', 'delete_evidence',
               'view_activity', 'delete_activity', 'view_validation')
        Employee.objects.create(
            institutional_id='ADM-A', user=cls.admin_a, delegation=cls.deleg_a,
            position=position, name='Admin A')

    def make_validation(self, evidence):
        return Validation.objects.create(
            evidence=evidence, employee=self.emp_a, decision='Aprobada',
            date=timezone.localdate(), notes='', result=True)


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class EvidenceDeleteTests(EvidenceDeleteTestData):
    def assertAlive(self, evidence):
        self.assertTrue(Evidence.objects.filter(pk=evidence.pk).exists())

    # --- Quién puede ---------------------------------------------------

    def test_anonymous_redirects_to_login_and_keeps_evidence(self):
        response = self.client.post(delete_url(self.ev_a))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={delete_url(self.ev_a)}")
        self.assertAlive(self.ev_a)

    def test_user_without_delete_permission_gets_403(self):
        # func_a puede ver y editar, pero no eliminar (como el Funcionario y
        # el Verificador del seed).
        self.client.force_login(self.func_a)
        self.assertEqual(self.client.post(delete_url(self.ev_a)).status_code, 403)
        self.assertAlive(self.ev_a)

    def test_user_without_any_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.post(delete_url(self.ev_a)).status_code, 403)
        self.assertAlive(self.ev_a)

    def test_other_delegation_evidence_is_404(self):
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.post(delete_url(self.ev_b)).status_code, 404)
        self.assertAlive(self.ev_b)

    def test_superuser_can_delete_in_any_delegation(self):
        self.client.force_login(self.root)
        response = self.client.post(delete_url(self.ev_b))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Evidence.objects.filter(pk=self.ev_b.pk).exists())

    # --- Cómo se pide --------------------------------------------------

    def test_get_is_not_allowed(self):
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.get(delete_url(self.ev_a)).status_code, 405)
        self.assertAlive(self.ev_a)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_a)
        self.assertEqual(client.post(delete_url(self.ev_a)).status_code, 403)
        self.assertAlive(self.ev_a)

    def test_token_rendered_in_the_list_page_is_accepted(self):
        # Extremo a extremo: el token que imprime el template es el que el
        # servidor acepta, con la verificación CSRF activa.
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_a)
        html = client.get(LIST_URL).content.decode()
        form = re.search(
            r'<form[^>]+action="%s".*?</form>' % re.escape(delete_url(self.ev_a)),
            html, re.S).group(0)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', form).group(1)
        response = client.post(delete_url(self.ev_a), {'csrfmiddlewaretoken': token})
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)
        self.assertFalse(Evidence.objects.filter(pk=self.ev_a.pk).exists())

    # --- Qué hace ------------------------------------------------------

    def test_delete_is_logical_the_row_stays_in_the_database(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(delete_url(self.ev_a), follow=True)
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Evidence.objects.filter(pk=self.ev_a.pk).exists())
        row = Evidence.all_objects.get(pk=self.ev_a.pk)  # sigue existiendo
        self.assertIsNotNone(row.deleted_at)
        self.assertIn('Evidencia eliminada.', message_texts(response))

    def test_file_stays_on_disk_so_the_row_can_be_restored(self):
        # Borrado lógico: solo se marca `deleted_at`; el archivo no se toca.
        name = self.ev_a.file.name
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.ev_a))
        row = Evidence.all_objects.get(pk=self.ev_a.pk)
        self.assertEqual(row.file.name, name)
        self.assertTrue(row.file.storage.exists(name))

    def test_deleted_evidence_disappears_from_the_list(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.ev_a))
        response = self.client.get(LIST_URL)
        self.assertEqual(list(response.context['evidences']), [])

    def test_second_submit_is_404_and_does_not_break(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.ev_a))
        self.assertEqual(self.client.post(delete_url(self.ev_a)).status_code, 404)

    def test_only_the_targeted_evidence_is_deleted(self):
        other = self._make_evidence('EVID-A2', self.act_a)
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.ev_a))
        self.assertAlive(other)

    def test_code_with_slash_can_be_deleted(self):
        # Un código así solo puede venir del Admin (el formulario web lo
        # rechaza), pero la ruta de eliminar debe entenderlo igual que la de
        # editar (`<path:pk>`): un converter `str` daría NoReverseMatch.
        odd = self._make_evidence('A/B', self.act_a)
        self.client.force_login(self.admin_a)
        self.assertContains(self.client.get(LIST_URL), f'action="{delete_url(odd)}"')
        response = self.client.post(delete_url(odd))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Evidence.objects.filter(pk='A/B').exists())
        self.assertIsNotNone(Evidence.all_objects.get(pk='A/B').deleted_at)

    # --- Cascada: la validación --------------------------------------------

    def test_deleting_evidence_also_deletes_its_validation(self):
        validation = self.make_validation(self.ev_a)
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.ev_a))
        self.assertFalse(Validation.objects.filter(pk=validation.pk).exists())
        self.assertIsNotNone(Validation.all_objects.get(pk=validation.pk).deleted_at)

    def test_deleted_validation_disappears_from_the_validation_list(self):
        self.make_validation(self.ev_a)
        self.client.force_login(self.admin_a)
        validation_list = reverse('performance:validation_list')
        self.assertEqual(len(self.client.get(validation_list).context['validations']), 1)
        self.client.post(delete_url(self.ev_a))
        self.assertEqual(len(self.client.get(validation_list).context['validations']), 0)

    def test_other_validations_are_not_touched(self):
        other = self._make_evidence('EVID-A2', self.act_a)
        kept = self.make_validation(other)
        self.make_validation(self.ev_a)
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.ev_a))
        self.assertTrue(Validation.objects.filter(pk=kept.pk).exists())

    # --- Se cierra la dependencia de Activity ----------------------------

    def test_activity_can_be_deleted_from_the_web_after_its_evidence(self):
        # Antes de este patch, el mensaje "Elimine primero sus evidencias" de
        # una actividad solo podía cumplirse desde el Admin.
        activity_delete = reverse('performance:activity_delete', args=[self.act_a.pk])
        self.client.force_login(self.admin_a)

        response = self.client.post(activity_delete, follow=True)
        self.assertTrue(any('evidencias' in m for m in message_texts(response)))
        self.assertTrue(Activity.objects.filter(pk=self.act_a.pk).exists())

        self.client.post(delete_url(self.ev_a))
        response = self.client.post(activity_delete, follow=True)
        self.assertRedirects(response, ACTIVITY_LIST_URL)
        self.assertFalse(Activity.objects.filter(pk=self.act_a.pk).exists())


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class EvidenceDeleteButtonTests(EvidenceDeleteTestData):
    """Lo que se dibuja en el listado según el permiso."""

    def test_button_and_scripts_only_with_delete_permission(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertContains(response, f'action="{delete_url(self.ev_a)}"')
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
        self.assertContains(response, delete_url(self.ev_a))
        self.assertNotContains(response, delete_url(self.ev_b))

    def test_dialog_warns_that_the_validation_is_deleted_too(self):
        self.client.force_login(self.admin_a)
        self.assertContains(self.client.get(LIST_URL), WARNING)

    def test_warning_is_fixed_and_costs_no_query_per_row(self):
        # El aviso no depende de si la fila tiene validación (Decisión 28):
        # preguntarlo por fila sumaría una consulta por cada evidencia.
        self.client.force_login(self.admin_a)
        self.client.get(LIST_URL)  # calienta sesión y permisos
        with CaptureQueriesContext(connection) as few:
            self.client.get(LIST_URL)
        for i in range(4):
            self.make_validation(self._make_evidence(f'EXTRA-{i}', self.act_a))
        with CaptureQueriesContext(connection) as many:
            response = self.client.get(LIST_URL)
        self.assertEqual(len(response.context['evidences']), 5)
        self.assertEqual(len(few), len(many))

    def test_confirmation_text_is_escaped_inside_the_attribute(self):
        # El texto del diálogo incluye el código (dato del registro): no puede
        # abrir ni cerrar el atributo ni inyectar etiquetas.
        odd = self._make_evidence('E"V <b>x</b>', self.act_a)
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, delete_url(odd))
        self.assertNotContains(response, '<b>x</b>')
        self.assertContains(response, 'E&quot;V &lt;b&gt;x&lt;/b&gt;')


class DeleteButtonPartialTests(SimpleTestCase):
    """El parámetro opcional `extra` del parcial compartido."""

    def render(self, **context):
        context = {'url': '/x/delete/', 'title': 'T', 'detail': 'D', **context}
        return render_to_string(
            'performance/partials/delete_button.html', context,
            request=RequestFactory().get('/'))

    def test_extra_is_appended_to_the_dialog_text(self):
        html = self.render(extra=WARNING)
        self.assertIn(f'dejará de mostrarse en el sistema. {WARNING}">Eliminar</button>', html)

    def test_without_extra_the_text_is_the_one_from_patch_12(self):
        html = self.render()
        self.assertIn('dejará de mostrarse en el sistema.">Eliminar</button>', html)

    def test_extra_is_escaped_even_when_it_is_a_template_literal(self):
        # Es el caso real de uso: `extra="..."` escrito en la plantilla del
        # listado. Django marca como seguros los literales de plantilla y no
        # los escapa, así que sin `force_escape` una comilla en `extra`
        # cerraría el atributo data-text. (Pasarlo por el contexto de Python
        # no sirve para probarlo: ahí Django sí lo escapa solo.)
        source = (
            '{% include "performance/partials/delete_button.html" '
            "with url='/x/delete/' title='T' detail='D' "
            "extra='Aviso \"con comillas\" <b>x</b>' %}"
        )
        html = engines['django'].from_string(source).render({}, RequestFactory().get('/'))
        self.assertNotIn('<b>x</b>', html)
        self.assertIn('Aviso &quot;con comillas&quot; &lt;b&gt;x&lt;/b&gt;', html)
