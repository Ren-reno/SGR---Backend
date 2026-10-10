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
from performance.models import Activity, CatalogItem, Evidence, Period

User = get_user_model()
PASSWORD = 'Clave-Prueba-2026!'


def _png_file():
    buf = BytesIO()
    Image.new('RGB', (1, 1)).save(buf, 'PNG')
    return SimpleUploadedFile('e.png', buf.getvalue(), content_type='image/png')


class ActivityApiTests(APITestCase):

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
        cls.period = Period.objects.create(
            start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
            computable_days=120, status='activo',
            amber_threshold=Decimal('80.00'),
            collective_threshold=Decimal('90.00'),
        )
        cls.attention = CatalogItem.objects.create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Atencion Test',
        )
        cls.inactive_attention = CatalogItem.objects.create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Atencion Inactiva',
            is_active=False,
        )

    # --- helpers -----------------------------------------------------------
    def payload(self, **overrides):
        data = {
            'employee': self.employee.pk,
            'period': self.period.pk,
            'activity_type': 'Visita',
            'service': 'Social',
            'attention': self.attention.pk,
            'sub_attention': 'General',
            'date': '2026-08-10',
            'request_description': 'Solicitud de prueba',
            'action_taken': 'Se atendio al vecino',
            'contact_name': 'Ana Perez',
            'contact_phone': '+56 9 1234 5678',
            'status': 'abierta',
        }
        data.update(overrides)
        return data

    def make_activity(self, description='Base'):
        return Activity.objects.create(
            employee=self.employee, period=self.period,
            activity_type='Visita', service='Social',
            attention=self.attention, sub_attention='General',
            date=date(2026, 8, 10), request_description=description,
            action_taken='x', status='abierta',
        )

    def list_url(self):
        return reverse('api:activity-list')

    def detail_url(self, pk):
        return reverse('api:activity-detail', args=[pk])

    # --- autenticacion y roles --------------------------------------------
    def test_sin_token_401(self):
        self.assertEqual(self.client.get(self.list_url()).status_code, 401)

    def test_sin_rol_403(self):
        self.client.force_authenticate(self.sinrol)
        self.assertEqual(self.client.get(self.list_url()).status_code, 403)

    def test_operador_lista_200_y_paginada(self):
        for i in range(26):
            self.make_activity(description=f'Solicitud {i}')
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 26)
        self.assertEqual(len(response.data['results']), 25)
        self.assertIsNotNone(response.data['next'])

    def test_operador_no_puede_crear_403(self):
        self.client.force_authenticate(self.operador)
        response = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Activity.objects.count(), 0)

    # --- crear y validar ---------------------------------------------------
    def test_admin_crea_201(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Activity.objects.count(), 1)

    def test_telefono_invalido_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(contact_phone='abc'), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('contact_phone', response.data)
        self.assertEqual(Activity.objects.count(), 0)

    def test_fecha_fuera_de_periodo_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(date='2027-01-15'), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('date', response.data)

    def test_duplicado_400(self):
        self.client.force_authenticate(self.admin)
        first = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Activity.objects.count(), 1)

    def test_atencion_inactiva_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(),
            self.payload(attention=self.inactive_attention.pk),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('attention', response.data)

    def test_campo_obligatorio_faltante_400(self):
        self.client.force_authenticate(self.admin)
        data = self.payload()
        del data['activity_type']
        response = self.client.post(self.list_url(), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('activity_type', response.data)

    # --- detalle, actualizar, eliminar ------------------------------------
    def test_detalle_inexistente_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.detail_url(999999)).status_code, 404)

    def test_admin_actualiza_parcial_200(self):
        activity = self.make_activity()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.detail_url(activity.pk), {'status': 'cerrada'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        activity.refresh_from_db()
        self.assertEqual(activity.status, 'cerrada')

    def test_admin_elimina_logico_204(self):
        activity = self.make_activity()
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail_url(activity.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Activity.objects.filter(pk=activity.pk).exists())
        self.assertTrue(Activity.all_objects.filter(pk=activity.pk).exists())
        self.assertEqual(self.client.get(self.detail_url(activity.pk)).status_code, 404)

    def test_eliminar_con_evidencia_409(self):
        activity = self.make_activity()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                Evidence.objects.create(
                    activity=activity, file=_png_file(), date=date(2026, 8, 11),
                )
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail_url(activity.pk))
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Activity.objects.filter(pk=activity.pk).exists())