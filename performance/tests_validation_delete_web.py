"""Pruebas de la eliminación web de Validation (Fase 6, paso 6.3 / Fase 7,
Decisión 29).

Por HTTP (Client) contra las URLs reales, igual que las de `Activity` y
`Evidence` (`tests_activity_delete_web.py`, `tests_evidence_delete_web.py`).
El token CSRF se prueba con `Client(enforce_csrf_checks=True)`, porque el
Client normal lo salta y no detectaría un formulario sin token.

Lo propio de `Validation` frente a las otras entidades: además del permiso
`delete_validation` y de la Delegación, la vista exige el ROL de revisor
(Verificador o Administrador), igual que `ValidationAdmin.has_delete_permission`.
Correr con:  python manage.py test performance.tests_validation_delete_web
"""
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from organization.models import Employee, Position
from performance.models import Evidence, Validation
from performance.tests_validation_web import (
    VALIDATION_PERMS, ValidationWebTestData, _perms,
)

User = get_user_model()

LIST_URL = reverse('performance:validation_list')
EVIDENCE_LIST_URL = reverse('performance:evidence_list')
CREATE_URL = reverse('performance:validation_create')
WARNING = ('La evidencia quedará sin validación y no podrá volver a '
           'validarse desde la web.')


def delete_url(validation):
    return reverse('performance:validation_delete', args=[validation.pk])


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


class ValidationDeleteTestData(ValidationWebTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        position = Position.objects.get(name='Cargo')
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        verifier_group, _ = Group.objects.get_or_create(name='Verificador')

        def make(username, *, perms, group=None, delegation=None):
            user = User.objects.create_user(username, password='x')
            _perms(user, *perms)
            if group:
                user.groups.add(group)
            employee = None
            if delegation:
                employee = Employee.objects.create(
                    institutional_id=f'EMP-{username}', user=user,
                    delegation=delegation, position=position, name=username)
            return user, employee

        # Perfil "elimina": como el grupo Administrador del seed, pero SIN ser
        # superuser. Desde la Decisión 31 el grupo Administrador tampoco queda
        # acotado por Delegación (igual que en el Admin), así que este perfil
        # NO sirve para probar el 404 de scoping: para eso están `verif_del_a`
        # y `verif_del_no_employee`, que tienen rol y permiso pero no son
        # Administrador.
        cls.admin_a, _ = make(
            'admin_a', perms=('view_validation', 'delete_validation'),
            group=admin_group, delegation=cls.deleg_a)
        # Verificador al que alguien le dio `delete_validation` a mano (el
        # seed solo se lo da al Administrador): rol y permiso, Delegación A.
        cls.verif_del_a, _ = make(
            'verif_del_a', perms=VALIDATION_PERMS + ('delete_validation',),
            group=verifier_group, delegation=cls.deleg_a)
        # Tiene el permiso de eliminar pero NO el rol de revisor: es la regla
        # de `ValidationAdmin.has_delete_permission` que el permiso de modelo,
        # por sí solo, no cubre.
        cls.no_role_del, _ = make(
            'no_role_del', perms=('view_validation', 'delete_validation'),
            delegation=cls.deleg_a)
        # Administrador con permiso pero sin fila Employee (caso borde):
        # sin restricción de Delegación, como en el Admin (Decisión 31).
        cls.admin_no_employee, _ = make(
            'admin_no_employee', perms=('view_validation', 'delete_validation'),
            group=admin_group)
        # Rol de revisor y permiso, sin fila Employee y sin ser Administrador:
        # el caso borde que sí queda sin acceso (404, nunca 500).
        cls.verif_del_no_employee, _ = make(
            'verif_del_no_employee', perms=('view_validation', 'delete_validation'),
            group=verifier_group)

    def make_validation(self, evidence, decision='Aprobada'):
        return Validation.objects.create(
            evidence=evidence, employee=self.emp_verif_a, decision=decision,
            date=self.review_date, result=decision == 'Aprobada')


class ValidationDeleteTests(ValidationDeleteTestData):
    def assertAlive(self, validation):
        self.assertTrue(Validation.objects.filter(pk=validation.pk).exists())

    def test_url_is_the_documented_one(self):
        # El README documenta `/validations/<id>/delete/`; el resto de los
        # tests usan `reverse()` y no verían un cambio del texto de la ruta.
        self.assertEqual(
            delete_url(self.val_a), f'/validations/{self.val_a.pk}/delete/')

    # --- Quién puede ---------------------------------------------------

    def test_anonymous_redirects_to_login_and_keeps_validation(self):
        response = self.client.post(delete_url(self.val_a))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={delete_url(self.val_a)}")
        self.assertAlive(self.val_a)

    def test_verifier_without_delete_permission_gets_403(self):
        # verif_a ve, crea y edita, pero no elimina (como el Verificador del
        # seed): tiene el rol pero no el permiso.
        self.client.force_login(self.verif_a)
        self.assertEqual(self.client.post(delete_url(self.val_a)).status_code, 403)
        self.assertAlive(self.val_a)

    def test_user_without_any_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.post(delete_url(self.val_a)).status_code, 403)
        self.assertAlive(self.val_a)

    def test_delete_permission_without_reviewer_role_gets_403(self):
        # Permiso `delete_validation` sin ser Verificador ni Administrador:
        # `ValidationAdmin.has_delete_permission` lo bloquea, y la web también.
        self.client.force_login(self.no_role_del)
        self.assertEqual(self.client.post(delete_url(self.val_a)).status_code, 403)
        self.assertAlive(self.val_a)

    def test_permission_and_role_are_checked_before_delegation(self):
        # Sin rol de revisor y sobre una validación AJENA: responde 403 (no
        # 404), así que quien no puede eliminar nada no averigua qué
        # validaciones existen en otras Delegaciones.
        self.client.force_login(self.no_role_del)
        self.assertEqual(self.client.post(delete_url(self.val_b)).status_code, 403)
        self.client.force_login(self.verif_a)  # rol sí, permiso no
        self.assertEqual(self.client.post(delete_url(self.val_b)).status_code, 403)
        self.assertAlive(self.val_b)

    def test_other_delegation_validation_is_404(self):
        self.client.force_login(self.verif_del_a)
        self.assertEqual(self.client.post(delete_url(self.val_b)).status_code, 404)
        self.assertAlive(self.val_b)

    def test_scoping_follows_the_evidence_delegation_not_the_verifier(self):
        # Como la fila del seed: EVID-002 (Norte) validada por un verificador
        # de otra Delegación (Centro). El alcance lo da la evidencia, igual
        # que en el listado y en `ValidationAdmin`; si se mirara al
        # verificador, estos dos casos darían el resultado contrario.
        mine_checked_elsewhere = Validation.objects.create(
            evidence=self.ev_a1, employee=self.emp_verif_b, decision='Aprobada',
            date=self.review_date, result=True)
        theirs_checked_by_me = Validation.objects.create(
            evidence=self.ev_b1, employee=self.emp_verif_a, decision='Aprobada',
            date=self.review_date, result=True)
        self.client.force_login(self.verif_del_a)
        self.assertEqual(
            self.client.post(delete_url(theirs_checked_by_me)).status_code, 404)
        self.assertAlive(theirs_checked_by_me)
        response = self.client.post(delete_url(mine_checked_elsewhere))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(
            Validation.objects.filter(pk=mine_checked_elsewhere.pk).exists())

    def test_user_without_employee_gets_404_not_500(self):
        self.client.force_login(self.verif_del_no_employee)
        self.assertEqual(self.client.post(delete_url(self.val_a)).status_code, 404)
        self.assertAlive(self.val_a)

    def test_administrator_without_employee_is_unrestricted_like_the_admin(self):
        # Decisión 31: el grupo Administrador no depende de tener Employee ni
        # de tener una Delegación; el Admin ya se comporta así (Decisión 6).
        self.client.force_login(self.admin_no_employee)
        response = self.client.post(delete_url(self.val_a))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Validation.objects.filter(pk=self.val_a.pk).exists())

    def test_administrator_group_can_delete_in_another_delegation(self):
        # Decisión 31: antes era 404 (el scoping web solo eximía al superuser).
        self.client.force_login(self.admin_a)
        response = self.client.post(delete_url(self.val_b))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Validation.objects.filter(pk=self.val_b.pk).exists())

    def test_administrator_group_can_delete_in_own_delegation(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(delete_url(self.val_a))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Validation.objects.filter(pk=self.val_a.pk).exists())

    def test_verifier_with_delete_permission_can_delete_in_own_delegation(self):
        self.client.force_login(self.verif_del_a)
        response = self.client.post(delete_url(self.val_a))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Validation.objects.filter(pk=self.val_a.pk).exists())

    def test_verifier_with_delete_permission_cannot_touch_other_delegation(self):
        self.client.force_login(self.verif_del_a)
        self.assertEqual(self.client.post(delete_url(self.val_b)).status_code, 404)
        self.assertAlive(self.val_b)

    def test_superuser_can_delete_in_any_delegation(self):
        self.client.force_login(self.root)
        response = self.client.post(delete_url(self.val_b))
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Validation.objects.filter(pk=self.val_b.pk).exists())

    # --- Cómo se pide --------------------------------------------------

    def test_get_is_not_allowed(self):
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.get(delete_url(self.val_a)).status_code, 405)
        self.assertAlive(self.val_a)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_a)
        self.assertEqual(client.post(delete_url(self.val_a)).status_code, 403)
        self.assertAlive(self.val_a)

    def test_token_rendered_in_the_list_page_is_accepted(self):
        # Extremo a extremo: el token que imprime el template es el que el
        # servidor acepta, con la verificación CSRF activa.
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_a)
        html = client.get(LIST_URL).content.decode()
        form = re.search(
            r'<form[^>]+action="%s".*?</form>' % re.escape(delete_url(self.val_a)),
            html, re.S).group(0)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', form).group(1)
        response = client.post(delete_url(self.val_a), {'csrfmiddlewaretoken': token})
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)
        self.assertFalse(Validation.objects.filter(pk=self.val_a.pk).exists())

    # --- Qué hace ------------------------------------------------------

    def test_delete_is_logical_the_row_stays_in_the_database(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(delete_url(self.val_a), follow=True)
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(Validation.objects.filter(pk=self.val_a.pk).exists())
        row = Validation.all_objects.get(pk=self.val_a.pk)  # sigue existiendo
        self.assertIsNotNone(row.deleted_at)
        self.assertIn('Validación eliminada.', message_texts(response))

    def test_deleted_validation_disappears_from_the_list(self):
        self.client.force_login(self.verif_del_a)
        self.assertEqual(len(self.client.get(LIST_URL).context['validations']), 1)
        self.client.post(delete_url(self.val_a))
        self.assertEqual(list(self.client.get(LIST_URL).context['validations']), [])

    def test_second_submit_is_404_and_does_not_break(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.val_a))
        self.assertEqual(self.client.post(delete_url(self.val_a)).status_code, 404)

    def test_only_the_targeted_validation_is_deleted(self):
        other = self.make_validation(self.ev_a1)
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.val_a))
        self.assertAlive(other)
        self.assertAlive(self.val_b)

    def test_rejected_validation_can_be_deleted_too(self):
        rejected = Validation.objects.create(
            evidence=self.ev_a1, employee=self.emp_verif_a,
            decision='Rechazada', date=self.review_date, result=False,
            notes='Archivo ilegible')
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(rejected))
        self.assertIsNotNone(Validation.all_objects.get(pk=rejected.pk).deleted_at)

    # --- Efectos sobre la evidencia ----------------------------------------

    def test_evidence_is_not_deleted(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.val_a))
        evidence = Evidence.objects.get(pk=self.ev_a_done.pk)
        self.assertIsNone(evidence.deleted_at)

    def test_evidence_review_status_is_not_touched(self):
        # Decisión 24 punto 6 y Decisión 9-bis: `review_status` solo cambia
        # con la acción masiva del Admin. Eliminar una validación no lo toca.
        Evidence.objects.filter(pk=self.ev_a_done.pk).update(
            review_status=Evidence.REVIEW_STATUS_APROBADA)
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.val_a))
        self.assertEqual(
            Evidence.objects.get(pk=self.ev_a_done.pk).review_status,
            Evidence.REVIEW_STATUS_APROBADA)

    def test_evidence_can_be_deleted_afterwards(self):
        # La validación ya eliminada no debe hacer fallar la cascada de
        # `Evidence._before_soft_delete` (Decisión 26 punto 2).
        self.client.force_login(self.root)
        self.client.post(delete_url(self.val_a))
        evidence_delete = reverse(
            'performance:evidence_delete', args=[self.ev_a_done.pk])
        response = self.client.post(evidence_delete)
        self.assertRedirects(response, EVIDENCE_LIST_URL)
        self.assertIsNotNone(
            Evidence.all_objects.get(pk=self.ev_a_done.pk).deleted_at)

    # --- Limitación aceptada: sentido único (Decisión 29) ----------------

    def test_evidence_is_not_offered_again_after_deleting_its_validation(self):
        # La fila eliminada sigue ocupando el OneToOne, así que el
        # desplegable de `ValidationForm` no vuelve a ofrecer la evidencia.
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.val_a))
        self.client.force_login(self.verif_a)
        form = self.client.get(CREATE_URL).context['form']
        offered = set(form.fields['evidence'].queryset.values_list('pk', flat=True))
        self.assertNotIn(self.ev_a_done.pk, offered)
        self.assertIn(self.ev_a1.pk, offered)  # las demás siguen disponibles

    def test_revalidating_the_evidence_from_the_web_is_rejected_without_500(self):
        self.client.force_login(self.admin_a)
        self.client.post(delete_url(self.val_a))
        self.client.force_login(self.verif_a)
        before = Validation.all_objects.count()
        response = self.client.post(
            CREATE_URL, self.payload(evidence=self.ev_a_done))
        self.assertEqual(response.status_code, 200)
        self.assertIn('evidence', response.context['form'].errors)
        self.assertEqual(Validation.all_objects.count(), before)


class ValidationDeleteButtonTests(ValidationDeleteTestData):
    """Lo que se dibuja en el listado según el permiso y el rol."""

    def test_button_and_scripts_with_permission_and_role(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertContains(response, f'action="{delete_url(self.val_a)}"')
        self.assertContains(response, 'js-confirm-delete')
        self.assertContains(response, '/static/performance/vendor/sweetalert2/sweetalert2.all.min.js')
        self.assertContains(response, '/static/performance/js/confirm-delete.js')
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_verifier_with_delete_permission_sees_the_button(self):
        self.client.force_login(self.verif_del_a)
        self.assertContains(
            self.client.get(LIST_URL), f'action="{delete_url(self.val_a)}"')

    def test_no_button_and_no_scripts_without_delete_permission(self):
        # verif_a ve y edita, pero no elimina.
        self.client.force_login(self.verif_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar')
        self.assertNotContains(response, 'js-confirm-delete')
        self.assertNotContains(response, 'sweetalert2')
        self.assertNotContains(response, '/delete/')

    def test_no_button_and_no_scripts_with_permission_but_without_role(self):
        # El botón llevaría a un 403: no se muestra (mismo criterio que
        # "Nueva validación" y "Editar", que también exigen el rol).
        self.client.force_login(self.no_role_del)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'js-confirm-delete')
        self.assertNotContains(response, 'sweetalert2')
        self.assertNotContains(response, '/delete/')

    def test_only_rows_of_own_delegation_get_a_button(self):
        self.client.force_login(self.verif_del_a)
        response = self.client.get(LIST_URL)
        self.assertContains(response, delete_url(self.val_a))
        self.assertNotContains(response, delete_url(self.val_b))

    def test_administrator_group_sees_a_button_on_every_row(self):
        # Decisión 31: el grupo Administrador (sin ser superuser) ve las
        # validaciones de todas las Delegaciones, como en el Admin.
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertContains(response, delete_url(self.val_a))
        self.assertContains(response, delete_url(self.val_b))

    def test_superuser_sees_a_button_on_every_row(self):
        self.client.force_login(self.root)
        response = self.client.get(LIST_URL)
        self.assertContains(response, delete_url(self.val_a))
        self.assertContains(response, delete_url(self.val_b))

    def test_dialog_warns_that_revalidating_is_not_possible_from_the_web(self):
        self.client.force_login(self.admin_a)
        self.assertContains(self.client.get(LIST_URL), WARNING)

    def test_warning_is_fixed_and_costs_no_query_per_row(self):
        # El aviso es el mismo para todas las filas: no consulta nada por fila.
        # Usuario acotado a la Delegación A: el listado tiene 1 fila al inicio.
        self.client.force_login(self.verif_del_a)
        self.client.get(LIST_URL)  # calienta sesión y permisos
        with CaptureQueriesContext(connection) as few:
            self.client.get(LIST_URL)
        for i in range(4):
            evidence = Evidence.objects.create(
                code=f'EXTRA-{i}', activity=self.act_a, file='evidence/x.pdf',
                date=self.evidence_date)
            self.make_validation(evidence)
        with CaptureQueriesContext(connection) as many:
            response = self.client.get(LIST_URL)
        self.assertEqual(len(response.context['validations']), 5)
        self.assertEqual(len(few), len(many))

    def test_confirmation_text_is_escaped_inside_the_attribute(self):
        # El texto del diálogo incluye el código de la evidencia (dato del
        # registro): no puede abrir ni cerrar el atributo ni inyectar etiquetas.
        odd = Evidence.objects.create(
            code='E"V <b>x</b>', activity=self.act_a, file='evidence/x.pdf',
            date=self.evidence_date)
        validation = self.make_validation(odd)
        self.client.force_login(self.admin_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, delete_url(validation))
        self.assertNotContains(response, '<b>x</b>')
        self.assertContains(response, 'E&quot;V &lt;b&gt;x&lt;/b&gt;')
