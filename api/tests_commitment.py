from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from api.permissions import GROUP_API_ADMIN, GROUP_API_OPERADOR
from organization.models import Delegation, Employee, Position
from performance.models import Commitment

User = get_user_model()
PASSWORD = 'Clave-Prueba-2026!'


class CommitmentApiTests(APITestCase):

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
        cls.other_delegation = Delegation.objects.create(
            id='DEL-T2', name='Otra Delegacion', scope='Test 2',
        )
        position = Position.objects.create(name='Cargo Test')
        emp_user = User.objects.create_user('t_empleado', password=PASSWORD)
        cls.employee = Employee.objects.create(
            institutional_id='EMP-T1', user=emp_user,
            delegation=cls.delegation, position=position,
            name='Funcionario Test',
        )

    # --- helpers -----------------------------------------------------------
    def future(self, days=10):
        return timezone.localdate() + timedelta(days=days)

    def payload(self, **overrides):
        data = {
            'delegation': self.delegation.pk,
            'responsible': self.employee.pk,
            'origin': 'Oficio 123',
            'requester': 'Junta de Vecinos',
            'territory': 'Sector Norte',
            'due_date': self.future().isoformat(),
            'support_area': 'Obras',
            'status': 'ingresado',
            'observation': 'Compromiso de prueba',
        }
        data.update(overrides)
        return data

    def make_commitment(self, origin='Base', due_date=None):
        return Commitment.objects.create(
            delegation=self.delegation, responsible=self.employee,
            origin=origin, requester='Solicitante', territory='Territorio',
            due_date=due_date or self.future(), status='ingresado',
        )

    def list_url(self):
        return reverse('api:commitment-list')

    def detail_url(self, pk):
        return reverse('api:commitment-detail', args=[pk])

    # --- autenticacion y roles --------------------------------------------
    def test_sin_token_401(self):
        self.assertEqual(self.client.get(self.list_url()).status_code, 401)

    def test_sin_rol_403(self):
        self.client.force_authenticate(self.sinrol)
        self.assertEqual(self.client.get(self.list_url()).status_code, 403)

    def test_operador_lista_200_y_paginada(self):
        for i in range(26):
            self.make_commitment(origin=f'Origen {i}')
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 26)
        self.assertEqual(len(response.data['results']), 25)
        self.assertIsNotNone(response.data['next'])

    def test_operador_detalle_200(self):
        commitment = self.make_commitment()
        self.client.force_authenticate(self.operador)
        response = self.client.get(self.detail_url(commitment.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['origin'], 'Base')
        self.assertNotIn('deleted_at', response.data)

    def test_operador_no_puede_crear_403(self):
        self.client.force_authenticate(self.operador)
        response = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Commitment.objects.count(), 0)

    def test_operador_no_puede_modificar_ni_borrar_403(self):
        commitment = self.make_commitment()
        self.client.force_authenticate(self.operador)
        url = self.detail_url(commitment.pk)
        self.assertEqual(
            self.client.patch(url, {'status': 'realizado'}, format='json').status_code, 403,
        )
        self.assertEqual(
            self.client.put(url, self.payload(), format='json').status_code, 403,
        )
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertTrue(Commitment.objects.filter(pk=commitment.pk).exists())

    # --- crear y validar ---------------------------------------------------
    def test_admin_crea_201(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Commitment.objects.count(), 1)

    def test_delegacion_incongruente_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(),
            self.payload(delegation=self.other_delegation.pk),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('delegation', response.data)
        self.assertEqual(Commitment.objects.count(), 0)

    def test_fecha_pasada_al_crear_400(self):
        self.client.force_authenticate(self.admin)
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.client.post(
            self.list_url(), self.payload(due_date=yesterday), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('due_date', response.data)
        self.assertEqual(Commitment.objects.count(), 0)

    def test_fecha_de_hoy_es_valida(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(),
            self.payload(due_date=timezone.localdate().isoformat()),
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_duplicado_400(self):
        self.client.force_authenticate(self.admin)
        first = self.client.post(self.list_url(), self.payload(), format='json')
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(
            self.list_url(), self.payload(origin='OFICIO 123'), format='json',
        )
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Commitment.objects.count(), 1)

    def test_estado_invalido_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url(), self.payload(status='inexistente'), format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('status', response.data)

    def test_campo_obligatorio_faltante_400(self):
        self.client.force_authenticate(self.admin)
        data = self.payload()
        del data['origin']
        response = self.client.post(self.list_url(), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('origin', response.data)

    # --- detalle, actualizar, eliminar ------------------------------------
    def test_detalle_inexistente_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.detail_url(999999)).status_code, 404)

    def test_admin_actualiza_parcial_200(self):
        commitment = self.make_commitment()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.detail_url(commitment.pk), {'status': 'en_proceso'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        commitment.refresh_from_db()
        self.assertEqual(commitment.status, 'en_proceso')

    def test_admin_actualiza_completo_put_200(self):
        commitment = self.make_commitment()
        self.client.force_authenticate(self.admin)
        response = self.client.put(
            self.detail_url(commitment.pk),
            self.payload(origin='Origen editado', status='pendiente'),
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        commitment.refresh_from_db()
        self.assertEqual(commitment.origin, 'Origen editado')

    def test_compromiso_vencido_se_edita_sin_tocar_la_fecha(self):
        past = timezone.localdate() - timedelta(days=30)
        commitment = self.make_commitment(due_date=past)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.detail_url(commitment.pk), {'status': 'realizado'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        commitment.refresh_from_db()
        self.assertEqual(commitment.status, 'realizado')
        self.assertEqual(commitment.due_date, past)

    def test_put_vencido_con_misma_fecha_no_se_rechaza(self):
        past = timezone.localdate() - timedelta(days=30)
        commitment = self.make_commitment(due_date=past)
        self.client.force_authenticate(self.admin)
        response = self.client.put(
            self.detail_url(commitment.pk),
            self.payload(due_date=past.isoformat(), status='realizado'),
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_cambiar_la_fecha_a_una_pasada_400(self):
        commitment = self.make_commitment()
        self.client.force_authenticate(self.admin)
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.client.patch(
            self.detail_url(commitment.pk), {'due_date': yesterday}, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('due_date', response.data)

    def test_patch_delegacion_incongruente_400(self):
        commitment = self.make_commitment()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.detail_url(commitment.pk),
            {'delegation': self.other_delegation.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('delegation', response.data)

    def test_admin_elimina_logico_204(self):
        commitment = self.make_commitment()
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail_url(commitment.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Commitment.objects.filter(pk=commitment.pk).exists())
        self.assertTrue(Commitment.all_objects.filter(pk=commitment.pk).exists())
        self.assertEqual(self.client.get(self.detail_url(commitment.pk)).status_code, 404)

    def test_eliminado_no_aparece_en_la_lista(self):
        commitment = self.make_commitment()
        self.client.force_authenticate(self.admin)
        self.client.delete(self.detail_url(commitment.pk))
        response = self.client.get(self.list_url())
        self.assertEqual(response.data['count'], 0)
