from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APITestCase

from api.permissions import GROUP_API_ADMIN, GROUP_API_OPERADOR
from organization.models import Delegation, Employee, Position
from performance import models as perf_models
from performance.models import Activity, CatalogItem, Period

User = get_user_model()
PASSWORD = 'Clave-Prueba-2026!'


class MetaApiTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        g_admin, _ = Group.objects.get_or_create(name=GROUP_API_ADMIN)
        g_oper, _ = Group.objects.get_or_create(name=GROUP_API_OPERADOR)
        cls.admin = User.objects.create_user('t_admin', password=PASSWORD)
        cls.admin.groups.add(g_admin)
        cls.operador = User.objects.create_user('t_operador', password=PASSWORD)
        cls.operador.groups.add(g_oper)
        cls.sinrol = User.objects.create_user('t_sinrol', password=PASSWORD)

        cls.delegation = Delegation.objects.create(
            id='DEL-T1', name='Delegacion Test', scope='Test',
        )
        cls.position = Position.objects.create(name='Cargo Test')
        cls.other_position = Position.objects.create(name='Otro Cargo')
        emp_user = User.objects.create_user('t_empleado', password=PASSWORD)
        cls.employee = Employee.objects.create(
            institutional_id='EMP-T1', user=emp_user,
            delegation=cls.delegation, position=cls.position,
            name='Funcionario Test',
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

    # --- helpers -----------------------------------------------------------
    def payload(self, **overrides):
        data = {
            'position': self.position.pk,
            'period': self.period.pk,
            'item_name': 'Atenciones mensuales',
            'target_value': '50.00',
            'unit': 'atenciones',
            'weight': '40.00',
        }
        data.update(overrides)
        return data

    def make_meta(self, weight='10.00', item_name='Base', position=None):
        return perf_models.Meta.objects.create(
            position=position or self.position, period=self.period,
            item_name=item_name, target_value=Decimal('10.00'),
            unit='u', weight=Decimal(weight),
        )

    def list_url(self):
        return reverse('api:meta-list')

    def detail_url(self, pk):
        return reverse('api:meta-detail', args=[pk])

    # --- autenticacion y roles --------------------------------------------
    def test_sin_token_401(self):
        self.assertEqual(self.client.get(self.list_url()).status_code, 401)

    def test_sin_rol_403(self):
        self.client.force_authenticate(self.sinrol)
        self.assertEqual(self.client.get(self.list_url()).status_code, 403)

    def test_operador_lista_200_y_paginada(self):
        for i in range(26):
            self.make_meta(weight='1.00', item_name=f'Meta {i}')
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 26)
        self.assertEqual(len(response.data['results']), 25)
        self.assertIsNotNone(response.data['next'])

    def test_operador_detalle_200(self):
        meta = self.make_meta()
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.detail_url(meta.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['item_name'], 'Base')

    def test_operador_no_puede_crear_403(self):
        self.client.force_authenticate(self.operador)
        response = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(perf_models.Meta.objects.count(), 0)

    def test_operador_no_puede_modificar_ni_borrar_403(self):
        meta = self.make_meta()
        self.client.force_authenticate(self.operador)
        url = self.detail_url(meta.pk)
        self.assertEqual(
            self.client.patch(url, {'unit': 'x'}, format='json').status_code, 403,
        )
        self.assertEqual(
            self.client.put(url, self.payload(), format='json').status_code, 403,
        )
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertTrue(perf_models.Meta.objects.filter(pk=meta.pk).exists())

    # --- crear y validar ---------------------------------------------------
    def test_admin_crea_201(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(perf_models.Meta.objects.count(), 1)

    def test_ponderadores_suman_exactamente_100_es_valido(self):
        self.make_meta(weight='60.00')
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(weight='40.00'), format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_suma_de_ponderadores_mayor_a_100_400(self):
        self.make_meta(weight='70.00')
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(weight='40.00'), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('weight', response.data)
        self.assertEqual(perf_models.Meta.objects.count(), 1)

    def test_suma_se_calcula_por_cargo(self):
        self.make_meta(weight='90.00')
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(),
            self.payload(position=self.other_position.pk, weight='90.00'),
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_valor_objetivo_cero_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(target_value='0'), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('target_value', response.data)

    def test_valor_objetivo_negativo_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(target_value='-5'), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('target_value', response.data)

    def test_campo_obligatorio_faltante_400(self):
        self.client.force_authenticate(self.admin)
        data = self.payload()
        del data['item_name']
        response = self.client.post(self.list_url(), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('item_name', response.data)

    def test_periodo_inexistente_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(period=999999), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('period', response.data)

    # --- detalle, actualizar, eliminar ------------------------------------
    def test_detalle_inexistente_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.detail_url(999999)).status_code, 404)

    def test_admin_actualiza_parcial_200(self):
        meta = self.make_meta()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.detail_url(meta.pk), {'unit': 'casos'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        meta.refresh_from_db()
        self.assertEqual(meta.unit, 'casos')

    def test_admin_actualiza_completo_put_200(self):
        meta = self.make_meta(weight='100.00')
        self.client.force_authenticate(self.admin)
        # La suma excluye a la propia meta: re-guardar con 100 % es valido.
        response = self.client.put(
            self.detail_url(meta.pk),
            self.payload(item_name='Editada', weight='100.00'),
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        meta.refresh_from_db()
        self.assertEqual(meta.item_name, 'Editada')

    def test_patch_que_supera_100_400(self):
        self.make_meta(weight='70.00', item_name='Otra')
        meta = self.make_meta(weight='20.00')
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.detail_url(meta.pk), {'weight': '40.00'}, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('weight', response.data)
        meta.refresh_from_db()
        self.assertEqual(meta.weight, Decimal('20.00'))

    def test_admin_elimina_fisico_204(self):
        meta = self.make_meta()
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail_url(meta.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(perf_models.Meta.objects.filter(pk=meta.pk).exists())
        self.assertEqual(self.client.get(self.detail_url(meta.pk)).status_code, 404)

    def test_eliminar_con_actividades_asociadas_409(self):
        meta = self.make_meta()
        Activity.objects.create(
            employee=self.employee, period=self.period, meta=meta,
            activity_type='Visita', service='Social',
            attention=self.attention, sub_attention='General',
            date=date(2026, 8, 10), request_description='Base',
            action_taken='x', status='abierta',
        )
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail_url(meta.pk))
        self.assertEqual(response.status_code, 409)
        self.assertIn('detail', response.data)
        self.assertTrue(perf_models.Meta.objects.filter(pk=meta.pk).exists())
