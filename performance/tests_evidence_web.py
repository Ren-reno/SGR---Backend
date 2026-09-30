"""Pruebas del CRUD web de Evidence (Fase 6, paso 6.2).

Se prueba por HTTP (Client), contra las URLs reales, igual que en 6.1. Los
archivos subidos van a un MEDIA_ROOT temporal para no ensuciar `media/`.
Correr con:  python manage.py test performance.tests_evidence_web
"""
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from organization.models import Delegation, Employee, Position
from performance.forms import EvidenceForm
from performance.models import Activity, CatalogItem, Evidence, Period

User = get_user_model()

_TEST_MEDIA = tempfile.mkdtemp(prefix='sgr-test-media-')


def _perms(user, *codenames):
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get_by_natural_key(
                codename, 'performance', codename.split('_', 1)[1]
            )
        )


def _upload(name='foto.pdf', content=b'%PDF-1.4 contenido de prueba'):
    return SimpleUploadedFile(name, content, content_type='application/pdf')


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class EvidenceWebTestData(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEST_MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.deleg_a = Delegation.objects.create(id='DEL-A', name='Delegación A', scope='x')
        cls.deleg_b = Delegation.objects.create(id='DEL-B', name='Delegación B', scope='x')
        position = Position.objects.create(name='Cargo')

        # Mismo perfil que el grupo Funcionario/Verificador del seed sobre
        # Evidence: ver y editar, no crear.
        cls.func_a = User.objects.create_user('func_a', password='x')
        _perms(cls.func_a, 'view_evidence', 'change_evidence')
        # Único perfil que crea en el seed es Administrador; aquí uno de
        # Delegación A con permisos de crear (y ver, para llegar al listado
        # tras guardar) sin ser superuser, para probar el acotado de `activity`.
        cls.adder_a = User.objects.create_user('adder_a', password='x')
        _perms(cls.adder_a, 'view_evidence', 'add_evidence')
        # Sin ningún permiso de modelo (como el grupo Delegado hoy).
        cls.sin_permiso = User.objects.create_user('sin_permiso', password='x')
        cls.root = User.objects.create_superuser('root', 'r@x.cl', 'x')
        user_b = User.objects.create_user('func_b', password='x')

        cls.emp_a = Employee.objects.create(
            institutional_id='EMP-A', user=cls.func_a, delegation=cls.deleg_a,
            position=position, name='Empleado A')
        Employee.objects.create(
            institutional_id='EMP-AD', user=cls.adder_a, delegation=cls.deleg_a,
            position=position, name='Empleado Adder')
        cls.emp_b = Employee.objects.create(
            institutional_id='EMP-B', user=user_b, delegation=cls.deleg_b,
            position=position, name='Empleado B')

        cls.period = Period.objects.create(
            start_date='2026-01-01', end_date='2026-12-31', computable_days=200,
            status='abierto', amber_threshold='70.00', collective_threshold='90.00')
        cls.attention, _ = CatalogItem.objects.get_or_create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Atención test')

        cls.act_a = cls._make_activity(cls.emp_a, 'solicitud A')
        cls.act_b = cls._make_activity(cls.emp_b, 'solicitud B')

    @classmethod
    def _make_activity(cls, employee, description, date='2026-06-01'):
        return Activity.objects.create(
            employee=employee, period=cls.period, attention=cls.attention,
            activity_type='Primera Atención', service='s', sub_attention='sa',
            date=date, request_description=description, action_taken='a',
            status='Pendiente')

    def _make_evidence(self, code, activity, date='2026-06-02'):
        return Evidence.objects.create(
            code=code, activity=activity, date=date, file=_upload(f'{code}.pdf'))

    def setUp(self):
        self.ev_a = self._make_evidence('EVID-A', self.act_a)
        self.ev_b = self._make_evidence('EVID-B', self.act_b)

    def payload(self, activity=None, **overrides):
        data = {
            'code': 'EVID-NEW',
            'activity': (activity or self.act_a).pk,
            'date': '2026-06-05',
            'metadata': 'Foto de prueba',
            'file': _upload('nueva.pdf'),
        }
        data.update(overrides)
        return data


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class EvidenceListTests(EvidenceWebTestData):
    url = reverse('performance:evidence_list')

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
        self.assertEqual(list(response.context['evidences']), [self.ev_a])
        self.assertNotContains(response, 'EVID-B')
        self.assertNotContains(response, 'Empleado B')

    def test_superuser_sees_all(self):
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertCountEqual(response.context['evidences'], [self.ev_a, self.ev_b])

    def test_soft_deleted_evidence_is_not_listed(self):
        self.ev_a.soft_delete()
        self.client.force_login(self.root)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['evidences']), [self.ev_b])

    def test_add_button_only_with_add_permission(self):
        create_url = reverse('performance:evidence_create')
        self.client.force_login(self.func_a)
        self.assertNotContains(self.client.get(self.url), create_url)
        self.client.force_login(self.root)
        self.assertContains(self.client.get(self.url), create_url)

    def test_edit_link_only_with_change_permission(self):
        edit_url = reverse('performance:evidence_update', args=['EVID-A'])
        self.client.force_login(self.func_a)
        self.assertContains(self.client.get(self.url), edit_url)
        self.client.force_login(self.adder_a)  # ve, pero no edita
        self.assertNotContains(self.client.get(self.url), edit_url)

    def test_lists_link_to_uploaded_file(self):
        self.client.force_login(self.func_a)
        self.assertContains(self.client.get(self.url), self.ev_a.file.url)

    def test_code_with_slash_does_not_break_the_list(self):
        # Un código así solo puede venir del Admin (el formulario web lo
        # rechaza); con un converter `str` haría fallar el listado entero.
        odd = self._make_evidence('A/B', self.act_a)
        self.client.force_login(self.func_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(odd, response.context['evidences'])
        edit_url = reverse('performance:evidence_update', args=['A/B'])
        self.assertEqual(self.client.get(edit_url).status_code, 200)

    def test_paginates_with_page_size_from_url(self):
        for i in range(7):
            self._make_evidence(f'EXTRA-{i}', self.act_a, date=f'2026-06-{i + 3:02d}')
        self.client.force_login(self.func_a)
        response = self.client.get(self.url, {'per_page': 5})
        self.assertEqual(len(response.context['evidences']), 5)
        self.assertTrue(response.context['page_obj'].has_next())
        page2 = self.client.get(self.url, {'page': 2})  # el tamaño quedó en sesión
        self.assertEqual(len(page2.context['evidences']), 3)


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class EvidenceCreateTests(EvidenceWebTestData):
    url = reverse('performance:evidence_create')

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_user_without_add_permission_gets_403(self):
        self.client.force_login(self.func_a)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        before = Evidence.objects.count()
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)
        self.assertEqual(Evidence.objects.count(), before)

    def test_form_is_multipart(self):
        self.client.force_login(self.root)
        self.assertContains(self.client.get(self.url), 'enctype="multipart/form-data"')

    def test_superuser_creates_evidence_with_file(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse('performance:evidence_list'))
        created = Evidence.objects.get(code='EVID-NEW')
        self.assertEqual(created.activity, self.act_a)
        self.assertTrue(created.file.name.startswith('evidence/'))
        with created.file.open('rb') as fh:
            self.assertEqual(fh.read(), b'%PDF-1.4 contenido de prueba')

    def test_non_superuser_with_add_permission_creates_on_own_delegation(self):
        self.client.force_login(self.adder_a)
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse('performance:evidence_list'))
        self.assertTrue(Evidence.objects.filter(code='EVID-NEW').exists())

    def test_cannot_attach_to_activity_of_other_delegation(self):
        # El bypass que el scoping de la vista, por sí solo, no cierra.
        self.client.force_login(self.adder_a)
        before = Evidence.objects.count()
        response = self.client.post(self.url, self.payload(activity=self.act_b))
        self.assertEqual(response.status_code, 200)
        self.assertIn('activity', response.context['form'].errors)
        self.assertEqual(Evidence.objects.count(), before)

    def test_file_is_required_on_create(self):
        self.client.force_login(self.root)
        data = self.payload()
        del data['file']
        before = Evidence.objects.count()
        response = self.client.post(self.url, data)
        self.assertIn('file', response.context['form'].errors)
        self.assertEqual(Evidence.objects.count(), before)

    def test_required_fields_are_enforced(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url, {})
        errors = response.context['form'].errors
        for field in ('code', 'activity', 'file', 'date'):
            self.assertIn(field, errors)

    def test_duplicate_code_is_rejected_case_insensitively(self):
        self.client.force_login(self.root)
        before = Evidence.objects.count()
        for code in ('EVID-A', 'evid-a'):
            response = self.client.post(self.url, self.payload(code=code))
            self.assertEqual(response.status_code, 200)
            self.assertIn('code', response.context['form'].errors)
        self.assertEqual(Evidence.objects.count(), before)

    def test_code_of_soft_deleted_evidence_cannot_be_reused(self):
        # La fila eliminada sigue ocupando la clave primaria: sin este
        # chequeo saldría un IntegrityError (500) al guardar. El código
        # idéntico también lo frena `SoftDeleteModel.validate_unique`; la
        # variante con otras mayúsculas (test siguiente) solo la frena el
        # formulario.
        self.ev_a.soft_delete()
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload(code='EVID-A'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('code', response.context['form'].errors)

    def test_case_variant_of_soft_deleted_code_cannot_be_reused(self):
        self.ev_a.soft_delete()
        self.client.force_login(self.root)
        before = Evidence.all_objects.count()
        response = self.client.post(self.url, self.payload(code='evid-a'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('code', response.context['form'].errors)
        self.assertEqual(Evidence.all_objects.count(), before)

    def test_invalid_code_format_is_rejected(self):
        self.client.force_login(self.root)
        before = Evidence.objects.count()
        for code in ('EV 01', 'EV/01', 'EV.01', 'ÉV-01'):
            response = self.client.post(self.url, self.payload(code=code))
            self.assertIn('code', response.context['form'].errors, code)
        self.assertEqual(Evidence.objects.count(), before)

    def test_code_longer_than_30_characters_is_rejected(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload(code='E' * 31))
        self.assertIn('code', response.context['form'].errors)

    def test_future_date_is_rejected(self):
        self.client.force_login(self.root)
        tomorrow = timezone.localdate() + timedelta(days=1)
        response = self.client.post(self.url, self.payload(date=tomorrow.isoformat()))
        self.assertIn('date', response.context['form'].errors)
        self.assertFalse(Evidence.objects.filter(code='EVID-NEW').exists())

    def test_date_before_activity_is_rejected(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload(date='2026-05-31'))
        self.assertIn('date', response.context['form'].errors)

    def test_date_equal_to_activity_date_is_accepted(self):
        self.client.force_login(self.root)
        response = self.client.post(self.url, self.payload(date='2026-06-01'))
        self.assertEqual(response.status_code, 302)

    def test_review_status_cannot_be_set_by_the_poster(self):
        # RN-009: solo una validación aprueba. Quien carga no puede mandar
        # `aprobada` en el POST; la evidencia nace con el default del modelo.
        self.client.force_login(self.root)
        self.client.post(self.url, self.payload(
            review_status=Evidence.REVIEW_STATUS_APROBADA))
        self.assertEqual(
            Evidence.objects.get(code='EVID-NEW').review_status,
            Evidence.REVIEW_STATUS_PENDIENTE)


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class EvidenceUpdateTests(EvidenceWebTestData):
    def url(self, evidence):
        return reverse('performance:evidence_update', args=[evidence.pk])

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url(self.ev_a))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={self.url(self.ev_a)}")

    def test_user_without_change_permission_gets_403(self):
        self.client.force_login(self.sin_permiso)
        self.assertEqual(self.client.get(self.url(self.ev_a)).status_code, 403)

    def test_edits_own_delegation_evidence(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.ev_a), {
            'activity': self.act_a.pk, 'date': '2026-06-03', 'metadata': 'editada'})
        self.assertRedirects(response, reverse('performance:evidence_list'))
        self.ev_a.refresh_from_db()
        self.assertEqual(self.ev_a.metadata, 'editada')
        self.assertEqual(str(self.ev_a.date), '2026-06-03')

    def test_form_prefilled_and_shows_current_file(self):
        self.client.force_login(self.func_a)
        response = self.client.get(self.url(self.ev_a))
        self.assertContains(response, 'value="2026-06-02"')
        self.assertContains(response, 'EVID-A')
        self.assertContains(response, self.ev_a.file.url)
        # review_status se muestra, pero como dato de solo lectura.
        self.assertContains(response, 'Estado de revisión')
        self.assertNotIn('review_status', response.context['form'].fields)

    def test_code_field_is_disabled_when_editing(self):
        self.client.force_login(self.func_a)
        form = self.client.get(self.url(self.ev_a)).context['form']
        self.assertTrue(form.fields['code'].disabled)

    def test_code_cannot_be_changed_by_post(self):
        # Sin `disabled`, cambiar el código haría que save() insertara una
        # fila nueva y dejara la original: dos evidencias en vez de una.
        self.client.force_login(self.func_a)
        before = Evidence.all_objects.count()
        response = self.client.post(self.url(self.ev_a), {
            'code': 'EVID-HACK', 'activity': self.act_a.pk,
            'date': '2026-06-03', 'metadata': 'x'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Evidence.all_objects.count(), before)
        self.assertFalse(Evidence.all_objects.filter(code='EVID-HACK').exists())
        self.ev_a.refresh_from_db()
        self.assertEqual(self.ev_a.metadata, 'x')

    def test_keeps_current_file_when_none_uploaded(self):
        old_name = self.ev_a.file.name
        self.client.force_login(self.func_a)
        self.client.post(self.url(self.ev_a), {
            'activity': self.act_a.pk, 'date': '2026-06-03', 'metadata': ''})
        self.ev_a.refresh_from_db()
        self.assertEqual(self.ev_a.file.name, old_name)

    def test_replaces_file_when_a_new_one_is_uploaded(self):
        old_name = self.ev_a.file.name
        self.client.force_login(self.func_a)
        self.client.post(self.url(self.ev_a), {
            'activity': self.act_a.pk, 'date': '2026-06-03', 'metadata': '',
            'file': _upload('reemplazo.pdf', b'%PDF-1.4 nuevo')})
        self.ev_a.refresh_from_db()
        self.assertNotEqual(self.ev_a.file.name, old_name)
        with self.ev_a.file.open('rb') as fh:
            self.assertEqual(fh.read(), b'%PDF-1.4 nuevo')

    def test_other_delegation_evidence_is_404(self):
        self.client.force_login(self.func_a)
        self.assertEqual(self.client.get(self.url(self.ev_b)).status_code, 404)
        response = self.client.post(self.url(self.ev_b), {
            'activity': self.act_b.pk, 'date': '2026-06-03', 'metadata': 'x'})
        self.assertEqual(response.status_code, 404)
        self.ev_b.refresh_from_db()
        self.assertEqual(self.ev_b.metadata, '')

    def test_cannot_reassign_to_activity_of_other_delegation(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.ev_a), {
            'activity': self.act_b.pk, 'date': '2026-06-03', 'metadata': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('activity', response.context['form'].errors)
        self.ev_a.refresh_from_db()
        self.assertEqual(self.ev_a.activity, self.act_a)

    def test_review_status_cannot_be_changed_by_post(self):
        self.client.force_login(self.func_a)
        self.client.post(self.url(self.ev_a), {
            'activity': self.act_a.pk, 'date': '2026-06-03', 'metadata': '',
            'review_status': Evidence.REVIEW_STATUS_APROBADA})
        self.ev_a.refresh_from_db()
        self.assertEqual(self.ev_a.review_status, Evidence.REVIEW_STATUS_PENDIENTE)

    def test_date_rules_also_apply_when_editing(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.ev_a), {
            'activity': self.act_a.pk, 'date': '2026-05-01', 'metadata': ''})
        self.assertIn('date', response.context['form'].errors)

    def test_saving_without_changes_is_not_a_duplicate_of_itself(self):
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(self.ev_a), {
            'activity': self.act_a.pk, 'date': '2026-06-02', 'metadata': ''})
        self.assertEqual(response.status_code, 302)

    def test_evidence_with_legacy_code_stays_editable(self):
        # Creada fuera del formulario (Admin/ORM) con un código que el
        # formulario web no aceptaría hoy: editarla no debe exigirle el formato.
        odd = self._make_evidence('EV 01/x', self.act_a)
        self.client.force_login(self.func_a)
        response = self.client.post(self.url(odd), {
            'activity': self.act_a.pk, 'date': '2026-06-03', 'metadata': 'ok'})
        self.assertEqual(response.status_code, 302)
        odd.refresh_from_db()
        self.assertEqual(odd.metadata, 'ok')

    def test_soft_deleted_evidence_is_404(self):
        self.ev_a.soft_delete()
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.url(self.ev_a)).status_code, 404)


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class EvidenceFormScopingTests(EvidenceWebTestData):
    def test_activity_choices_limited_to_own_delegation(self):
        form = EvidenceForm(user=self.func_a)
        self.assertEqual(list(form.fields['activity'].queryset), [self.act_a])

    def test_superuser_gets_all_activities(self):
        form = EvidenceForm(user=self.root)
        self.assertCountEqual(form.fields['activity'].queryset, [self.act_a, self.act_b])

    def test_user_without_employee_gets_no_activities(self):
        orphan = User.objects.create_user('orphan', password='x')
        self.assertEqual(list(EvidenceForm(user=orphan).fields['activity'].queryset), [])

    def test_soft_deleted_activity_is_not_offered(self):
        extra = self._make_activity(self.emp_a, 'para borrar', date='2026-06-10')
        extra.soft_delete()
        self.assertNotIn(extra, EvidenceForm(user=self.root).fields['activity'].queryset)

    def test_activity_label_identifies_the_activity(self):
        # Releída de la BD: `self.act_a` conserva la fecha como texto, tal
        # como se le pasó a create(), y el desplegable trabaja con `date`.
        activity = Activity.objects.get(pk=self.act_a.pk)
        label = EvidenceForm(user=self.root).fields['activity'].label_from_instance(activity)
        self.assertIn('Empleado A', label)
        self.assertIn('01/06/2026', label)
