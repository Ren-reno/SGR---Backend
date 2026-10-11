import tempfile
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APITestCase

from api.permissions import GROUP_API_ADMIN, GROUP_API_OPERADOR
from organization.models import Delegation, Employee, Position
from performance.models import Activity, CatalogItem, Evidence, Period, Validation

User = get_user_model()
PASSWORD = 'Clave-Prueba-2026!'

MEDIA_DIR = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)


def _png_file():
    buf = BytesIO()
    Image.new('RGB', (1, 1)).save(buf, 'PNG')
    return SimpleUploadedFile('e.png', buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA_DIR.name)
class OperationalApiTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        g_admin, _ = Group.objects.get_or_create(name=GROUP_API_ADMIN)
        g_oper, _ = Group.objects.get_or_create(name=GROUP_API_OPERADOR)
        cls.admin = User.objects.create_user('t_admin', password=PASSWORD)
        cls.admin.groups.add(g_admin)
        cls.operador = User.objects.create_user('t_operador', password=PASSWORD)
        cls.operador.groups.add(g_oper)
        cls.sinrol = User.objects.create_user('t_sinrol', password=PASSWORD)

        delegation = Delegation.objects.create(
            id='DEL-T1', name='Delegacion Test', scope='Test',
        )
        position = Position.objects.create(name='Cargo Test')
        emp_user = User.objects.create_user('t_empleado', password=PASSWORD)
        cls.employee = Employee.objects.create(
            institutional_id='EMP-T1', user=emp_user,
            delegation=delegation, position=position, name='Funcionario Test',
        )
        period = Period.objects.create(
            start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
            computable_days=120, status='activo',
            amber_threshold=Decimal('80.00'),
            collective_threshold=Decimal('90.00'),
        )
        attention = CatalogItem.objects.create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Atencion Test',
        )
        cls.activity = Activity.objects.create(
            employee=cls.employee, period=period,
            activity_type='Visita', service='Social',
            attention=attention, sub_attention='General',
            date=date(2026, 8, 10), request_description='Base',
            action_taken='x', status='abierta',
        )
        cls.evidence = Evidence.objects.create(
            activity=cls.activity, file=_png_file(), date=date(2026, 8, 11),
        )
        cls.validation = Validation.objects.create(
            evidence=cls.evidence, employee=cls.employee,
            decision='aprobada', date=date(2026, 8, 12),
            result=True,
        )

    # --- helpers -----------------------------------------------------------
    def ev_list(self):
        return reverse('api:evidence-list')

    def ev_detail(self, code):
        return reverse('api:evidence-detail', args=[code])

    def va_list(self):
        return reverse('api:validation-list')

    def va_detail(self, pk):
        return reverse('api:validation-detail', args=[pk])

    # --- autenticacion y roles --------------------------------------------
    def test_sin_token_401(self):
        self.assertEqual(self.client.get(self.ev_list()).status_code, 401)
        self.assertEqual(self.client.get(self.va_list()).status_code, 401)

    def test_sin_rol_403(self):
        self.client.force_authenticate(self.sinrol)
        self.assertEqual(self.client.get(self.ev_list()).status_code, 403)
        self.assertEqual(self.client.get(self.va_list()).status_code, 403)

    def test_admin_y_operador_listan_200(self):
        for user in (self.admin, self.operador):
            self.client.force_authenticate(user)
            ev = self.client.get(self.ev_list())
            va = self.client.get(self.va_list())
            self.assertEqual(ev.status_code, 200)
            self.assertEqual(va.status_code, 200)
            self.assertEqual(ev.data['count'], 1)
            self.assertEqual(va.data['count'], 1)

    # --- detalle -----------------------------------------------------------
    def test_detalle_evidence_por_codigo_200(self):
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.ev_detail(self.evidence.code))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], self.evidence.code)
        self.assertTrue(self.evidence.code.startswith('EVID-'))

    def test_file_se_expone_como_url_absoluta(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.ev_detail(self.evidence.code))
        self.assertTrue(response.data['file'].startswith('http'))
        self.assertIn('/media/evidence/', response.data['file'])

    def test_detalle_validation_200(self):
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.va_detail(self.validation.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['evidence'], self.evidence.code)
        self.assertEqual(response.data['decision'], 'aprobada')

    def test_codigo_inexistente_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.ev_detail('EVID-9999')).status_code, 404)
        self.assertEqual(self.client.get(self.va_detail(999999)).status_code, 404)

    # --- solo lectura ------------------------------------------------------
    def test_operador_no_puede_escribir_403(self):
        self.client.force_authenticate(self.operador)
        url = self.ev_detail(self.evidence.code)
        self.assertEqual(self.client.post(self.ev_list(), {}, format='json').status_code, 403)
        self.assertEqual(self.client.put(url, {}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(url, {}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertEqual(self.client.post(self.va_list(), {}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(self.va_detail(self.validation.pk)).status_code, 403)

    def test_admin_no_puede_escribir_405(self):
        self.client.force_authenticate(self.admin)
        url = self.ev_detail(self.evidence.code)
        self.assertEqual(self.client.post(self.ev_list(), {}, format='json').status_code, 405)
        self.assertEqual(self.client.put(url, {}, format='json').status_code, 405)
        self.assertEqual(self.client.patch(url, {}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        vurl = self.va_detail(self.validation.pk)
        self.assertEqual(self.client.post(self.va_list(), {}, format='json').status_code, 405)
        self.assertEqual(self.client.put(vurl, {}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(vurl).status_code, 405)
        self.assertTrue(Evidence.objects.filter(pk=self.evidence.pk).exists())
        self.assertTrue(Validation.objects.filter(pk=self.validation.pk).exists())

    # --- borrado logico ----------------------------------------------------
    def test_validacion_eliminada_no_aparece(self):
        self.validation.soft_delete()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.va_list()).data['count'], 0)
        self.assertEqual(
            self.client.get(self.va_detail(self.validation.pk)).status_code, 404,
        )

    def test_evidencia_eliminada_no_aparece(self):
        evidence = Evidence.objects.create(
            activity=self.activity, file=_png_file(), date=date(2026, 8, 13),
        )
        evidence.soft_delete()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.ev_list()).data['count'], 1)
        self.assertEqual(
            self.client.get(self.ev_detail(evidence.code)).status_code, 404,
        )

    # --- paginacion --------------------------------------------------------
    def test_lista_paginada_25(self):
        for i in range(26):
            Evidence.objects.create(
                activity=self.activity, file=_png_file(), date=date(2026, 8, 14),
            )
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.ev_list())
        self.assertEqual(response.data['count'], 27)
        self.assertEqual(len(response.data['results']), 25)
        self.assertIsNotNone(response.data['next'])
        page2 = self.client.get(self.ev_list(), {'page': 2})
        self.assertEqual(len(page2.data['results']), 2)