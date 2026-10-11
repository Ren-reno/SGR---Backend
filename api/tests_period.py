from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APITestCase

from api.permissions import GROUP_API_ADMIN, GROUP_API_OPERADOR
from organization.models import Position
from performance import models as perf_models
from performance.models import Period

User = get_user_model()
PASSWORD = 'Clave-Prueba-2026!'


class PeriodApiTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        g_admin, _ = Group.objects.get_or_create(name=GROUP_API_ADMIN)
        g_oper, _ = Group.objects.get_or_create(name=GROUP_API_OPERADOR)
        cls.admin = User.objects.create_user('t_admin', password=PASSWORD)
        cls.admin.groups.add(g_admin)
        cls.operador = User.objects.create_user('t_operador', password=PASSWORD)
        cls.operador.groups.add(g_oper)
        cls.sinrol = User.objects.create_user('t_sinrol', password=PASSWORD)
        cls.position = Position.objects.create(name='Cargo Test')

    # --- helpers -----------------------------------------------------------
    def payload(self, **overrides):
        data = {
            'start_date': '2026-07-01',
            'end_date': '2026-12-31',
            'computable_days': 120,
            'status': 'activo',
            'amber_threshold': '80.00',
            'collective_threshold': '90.00',
            'parameters_version': 1,
        }
        data.update(overrides)
        return data

    def make_period(self, start=date(2026, 7, 1), end=date(2026, 12, 31)):
        return Period.objects.create(
            start_date=start, end_date=end, computable_days=120,
            status='activo', amber_threshold=Decimal('80.00'),
            collective_threshold=Decimal('90.00'),
        )

    def list_url(self):
        return reverse('api:period-list')

    def detail_url(self, pk):
        return reverse('api:period-detail', args=[pk])

    # --- autenticacion y roles --------------------------------------------
    def test_sin_token_401(self):
        self.assertEqual(self.client.get(self.list_url()).status_code, 401)

    def test_sin_rol_403(self):
        self.client.force_authenticate(self.sinrol)
        self.assertEqual(self.client.get(self.list_url()).status_code, 403)

    def test_operador_lista_200_y_paginada(self):
        for i in range(26):
            self.make_period(start=date(2000 + i, 1, 1), end=date(2000 + i, 12, 31))
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 26)
        self.assertEqual(len(response.data['results']), 25)
        self.assertIsNotNone(response.data['next'])

    def test_operador_detalle_200(self):
        period = self.make_period()
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.detail_url(period.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'activo')

    def test_operador_no_puede_crear_403(self):
        self.client.force_authenticate(self.operador)
        response = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Period.objects.count(), 0)

    def test_operador_no_puede_modificar_ni_borrar_403(self):
        period = self.make_period()
        self.client.force_authenticate(self.operador)
        url = self.detail_url(period.pk)
        self.assertEqual(
            self.client.patch(url, {'status': 'cerrado'}, format='json').status_code, 403,
        )
        self.assertEqual(
            self.client.put(url, self.payload(), format='json').status_code, 403,
        )
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertTrue(Period.objects.filter(pk=period.pk).exists())

    # --- crear y validar ---------------------------------------------------
    def test_admin_crea_201(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Period.objects.count(), 1)

    def test_fechas_invertidas_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(),
            self.payload(start_date='2026-12-31', end_date='2026-07-01'),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('end_date', response.data)
        self.assertEqual(Period.objects.count(), 0)

    def test_periodo_de_un_dia_es_valido(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(),
            self.payload(start_date='2026-07-01', end_date='2026-07-01'),
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_umbral_mayor_a_100_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(amber_threshold='100.01'), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('amber_threshold', response.data)

    def test_umbral_negativo_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(collective_threshold='-1'), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('collective_threshold', response.data)

    def test_umbrales_en_los_limites_son_validos(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(),
            self.payload(amber_threshold='0', collective_threshold='100'),
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_campo_obligatorio_faltante_400(self):
        self.client.force_authenticate(self.admin)
        data = self.payload()
        del data['status']
        response = self.client.post(self.list_url(), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('status', response.data)

    # --- detalle, actualizar, eliminar ------------------------------------
    def test_detalle_inexistente_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.detail_url(999999)).status_code, 404)

    def test_admin_actualiza_parcial_200(self):
        period = self.make_period()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.detail_url(period.pk), {'status': 'cerrado'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        period.refresh_from_db()
        self.assertEqual(period.status, 'cerrado')

    def test_patch_fecha_fin_anterior_al_inicio_400(self):
        period = self.make_period()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.detail_url(period.pk), {'end_date': '2026-06-30'}, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('end_date', response.data)

    def test_admin_actualiza_completo_put_200(self):
        period = self.make_period()
        self.client.force_authenticate(self.admin)
        response = self.client.put(
            self.detail_url(period.pk),
            self.payload(status='cerrado', computable_days=100),
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        period.refresh_from_db()
        self.assertEqual(period.computable_days, 100)

    def test_admin_elimina_fisico_204(self):
        period = self.make_period()
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail_url(period.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Period.objects.filter(pk=period.pk).exists())
        self.assertEqual(self.client.get(self.detail_url(period.pk)).status_code, 404)

    def test_eliminar_con_metas_asociadas_409(self):
        period = self.make_period()
        perf_models.Meta.objects.create(
            position=self.position, period=period, item_name='M',
            target_value=Decimal('10'), unit='u', weight=Decimal('10'),
        )
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail_url(period.pk))
        self.assertEqual(response.status_code, 409)
        self.assertIn('detail', response.data)
        self.assertTrue(Period.objects.filter(pk=period.pk).exists())
