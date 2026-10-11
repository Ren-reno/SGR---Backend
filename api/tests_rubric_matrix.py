"""Prueba integral de la matriz de la rubrica (Evaluacion Sumativa 3).

Reproduce la tabla "Pruebas minimas en Apidog" sobre los 6 recursos de la
API: 401, 403, 200, CRUD completo, errores 400/404 y paginacion. Cada recurso
ya tiene sus propios tests (tests_activity, tests_commitment, tests_meta,
tests_period, tests_operational); aqui se prueba el cruce entre recursos,
roles y JWT.
"""
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from api.permissions import GROUP_API_ADMIN, GROUP_API_OPERADOR
from organization.models import Delegation, Employee, Position
from performance import models as perf_models
from performance.models import (
    Activity,
    CatalogItem,
    Commitment,
    Evidence,
    Period,
    Validation,
)

User = get_user_model()
PASSWORD = 'Clave-Prueba-2026!'
MEDIA_DIR = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

# Recursos con CRUD completo (admin escribe) y recursos de solo lectura.
PRINCIPALES = ['activity', 'commitment', 'meta', 'period']
OPERACIONALES = ['evidence', 'validation']
TODOS = PRINCIPALES + OPERACIONALES

PAGE_ROWS = 60  # filas creadas por recurso para probar la paginacion


def _png_file():
    buf = BytesIO()
    Image.new('RGB', (1, 1)).save(buf, 'PNG')
    return SimpleUploadedFile('e.png', buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA_DIR.name)
class RubricMatrixTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        g_admin, _ = Group.objects.get_or_create(name=GROUP_API_ADMIN)
        g_oper, _ = Group.objects.get_or_create(name=GROUP_API_OPERADOR)
        cls.admin = User.objects.create_user('m_admin', password=PASSWORD)
        cls.admin.groups.add(g_admin)
        cls.operador = User.objects.create_user('m_operador', password=PASSWORD)
        cls.operador.groups.add(g_oper)
        cls.sinrol = User.objects.create_user('m_sinrol', password=PASSWORD)

        cls.delegation = Delegation.objects.create(
            id='DEL-M1', name='Delegacion Matriz', scope='Test',
        )
        cls.position = Position.objects.create(name='Cargo Matriz')
        emp_user = User.objects.create_user('m_empleado', password=PASSWORD)
        cls.employee = Employee.objects.create(
            institutional_id='EMP-M1', user=emp_user,
            delegation=cls.delegation, position=cls.position,
            name='Funcionario Matriz',
        )
        cls.period = Period.objects.create(
            start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
            computable_days=120, status='activo',
            amber_threshold=Decimal('80.00'),
            collective_threshold=Decimal('90.00'),
        )
        cls.attention = CatalogItem.objects.create(
            category=CatalogItem.CATEGORY_ATTENTION, name='Atencion Matriz',
        )
        cls.activity = cls.make_activity('Base')
        cls.commitment = cls.make_commitment('Base')
        cls.meta = cls.make_meta('Base', weight='10.00')
        cls.evidence = Evidence.objects.create(
            activity=cls.activity, file=_png_file(), date=date(2026, 8, 11),
        )
        cls.validation = Validation.objects.create(
            evidence=cls.evidence, employee=cls.employee,
            decision='aprobada', date=date(2026, 8, 12), result=True,
        )

    # --- fabricas de datos ---------------------------------------------
    @classmethod
    def make_activity(cls, description):
        return Activity.objects.create(
            employee=cls.employee, period=cls.period,
            activity_type='Visita', service='Social',
            attention=cls.attention, sub_attention='General',
            date=date(2026, 8, 10), request_description=description,
            action_taken='x', status='abierta',
        )

    @classmethod
    def make_commitment(cls, origin):
        return Commitment.objects.create(
            delegation=cls.delegation, responsible=cls.employee,
            origin=origin, requester='Solicitante', territory='Territorio',
            due_date=timezone.localdate() + timedelta(days=10),
            status='ingresado',
        )

    @classmethod
    def make_meta(cls, item_name, weight='1.00'):
        return perf_models.Meta.objects.create(
            position=cls.position, period=cls.period, item_name=item_name,
            target_value=Decimal('10.00'), unit='u', weight=Decimal(weight),
        )

    # --- urls ------------------------------------------------------------
    def list_url(self, name):
        return reverse(f'api:{name}-list')

    def detail_url(self, name, pk=None):
        if pk is None:
            pk = {
                'activity': self.activity.pk,
                'commitment': self.commitment.pk,
                'meta': self.meta.pk,
                'period': self.period.pk,
                'evidence': self.evidence.code,
                'validation': self.validation.pk,
            }[name]
        return reverse(f'api:{name}-detail', args=[pk])

    def missing_url(self, name):
        pk = 'EVID-9999999' if name == 'evidence' else 999999
        return self.detail_url(name, pk)

    # --- 1. Sin token -> 401, sin rol -> 403, operador GET -> 200 --------
    def test_sin_token_401_en_lista_y_detalle(self):
        for name in TODOS:
            with self.subTest(recurso=name, tipo='lista'):
                self.assertEqual(self.client.get(self.list_url(name)).status_code, 401)
            with self.subTest(recurso=name, tipo='detalle'):
                self.assertEqual(self.client.get(self.detail_url(name)).status_code, 401)

    def test_token_invalido_401(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer token-falso')
        for name in TODOS:
            with self.subTest(recurso=name):
                self.assertEqual(self.client.get(self.list_url(name)).status_code, 401)

    def test_sin_rol_403_en_lista_y_detalle(self):
        self.client.force_authenticate(self.sinrol)
        for name in TODOS:
            with self.subTest(recurso=name, tipo='lista'):
                self.assertEqual(self.client.get(self.list_url(name)).status_code, 403)
            with self.subTest(recurso=name, tipo='detalle'):
                self.assertEqual(self.client.get(self.detail_url(name)).status_code, 403)

    def test_superusuario_sin_grupo_no_tiene_atajo_403(self):
        root = User.objects.create_superuser('m_root', password=PASSWORD)
        self.client.force_authenticate(root)
        for name in TODOS:
            with self.subTest(recurso=name):
                self.assertEqual(self.client.get(self.list_url(name)).status_code, 403)

    def test_operador_get_200_en_lista_y_detalle(self):
        self.client.force_authenticate(self.operador)
        for name in TODOS:
            with self.subTest(recurso=name, tipo='lista'):
                response = self.client.get(self.list_url(name))
                self.assertEqual(response.status_code, 200)
                self.assertGreaterEqual(response.data['count'], 1)
            with self.subTest(recurso=name, tipo='detalle'):
                self.assertEqual(self.client.get(self.detail_url(name)).status_code, 200)

    def test_operador_post_en_principales_403(self):
        self.client.force_authenticate(self.operador)
        for name in PRINCIPALES:
            with self.subTest(recurso=name):
                response = self.client.post(self.list_url(name), {}, format='json')
                self.assertEqual(response.status_code, 403)

    def test_operador_no_modifica_ni_borra_ningun_recurso_403(self):
        self.client.force_authenticate(self.operador)
        for name in TODOS:
            url = self.detail_url(name)
            with self.subTest(recurso=name):
                self.assertEqual(self.client.put(url, {}, format='json').status_code, 403)
                self.assertEqual(self.client.patch(url, {}, format='json').status_code, 403)
                self.assertEqual(self.client.delete(url).status_code, 403)

    def test_admin_get_200_en_lista_y_detalle(self):
        self.client.force_authenticate(self.admin)
        for name in TODOS:
            with self.subTest(recurso=name, tipo='lista'):
                self.assertEqual(self.client.get(self.list_url(name)).status_code, 200)
            with self.subTest(recurso=name, tipo='detalle'):
                self.assertEqual(self.client.get(self.detail_url(name)).status_code, 200)

    def test_operacionales_no_aceptan_escritura(self):
        # El permiso se evalua antes que el metodo: el admin recibe 405.
        self.client.force_authenticate(self.admin)
        for name in OPERACIONALES:
            with self.subTest(recurso=name):
                self.assertEqual(
                    self.client.post(self.list_url(name), {}, format='json').status_code, 405,
                )
                self.assertEqual(
                    self.client.delete(self.detail_url(name)).status_code, 405,
                )

    # --- 2. JWT: obtener y renovar token ---------------------------------
    def test_jwt_obtener_y_renovar_200(self):
        token = self.client.post(
            reverse('api:token_obtain_pair'),
            {'username': 'm_admin', 'password': PASSWORD}, format='json',
        )
        self.assertEqual(token.status_code, 200)
        self.assertIn('access', token.data)
        self.assertIn('refresh', token.data)

        refreshed = self.client.post(
            reverse('api:token_refresh'),
            {'refresh': token.data['refresh']}, format='json',
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn('access', refreshed.data)

    def test_jwt_credenciales_incorrectas_401(self):
        response = self.client.post(
            reverse('api:token_obtain_pair'),
            {'username': 'm_admin', 'password': 'incorrecta'}, format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_jwt_access_real_abre_los_6_recursos(self):
        token = self.client.post(
            reverse('api:token_obtain_pair'),
            {'username': 'm_operador', 'password': PASSWORD}, format='json',
        ).data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        for name in TODOS:
            with self.subTest(recurso=name):
                self.assertEqual(self.client.get(self.list_url(name)).status_code, 200)

    # --- 3. CRUD completo del admin: 201, 200, 200, 204 -------------------
    def test_crud_admin_period_borrado_fisico(self):
        self.client.force_authenticate(self.admin)
        payload = {
            'start_date': '2030-01-01', 'end_date': '2030-12-31',
            'computable_days': 200, 'status': 'activo',
            'amber_threshold': '70.00', 'collective_threshold': '85.00',
            'parameters_version': 1,
        }
        created = self.client.post(self.list_url('period'), payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        pk = created.data['id']
        url = self.detail_url('period', pk)

        self.assertEqual(self.client.get(url).status_code, 200)
        patched = self.client.patch(url, {'status': 'cerrado'}, format='json')
        self.assertEqual(patched.status_code, 200, patched.data)
        payload['computable_days'] = 150
        put = self.client.put(url, payload, format='json')
        self.assertEqual(put.status_code, 200, put.data)

        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertFalse(Period.objects.filter(pk=pk).exists())

    def test_crud_admin_commitment_borrado_logico(self):
        self.client.force_authenticate(self.admin)
        payload = {
            'delegation': self.delegation.pk,
            'responsible': self.employee.pk,
            'origin': 'Oficio matriz', 'requester': 'Junta de Vecinos',
            'territory': 'Sector Norte',
            'due_date': (timezone.localdate() + timedelta(days=20)).isoformat(),
            'support_area': 'Obras', 'status': 'ingresado',
            'observation': 'CRUD de la matriz',
        }
        created = self.client.post(self.list_url('commitment'), payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        pk = created.data['id']
        url = self.detail_url('commitment', pk)

        self.assertEqual(self.client.get(url).status_code, 200)
        patched = self.client.patch(url, {'status': 'en_proceso'}, format='json')
        self.assertEqual(patched.status_code, 200, patched.data)
        payload['status'] = 'realizado'
        put = self.client.put(url, payload, format='json')
        self.assertEqual(put.status_code, 200, put.data)

        # Borrado logico (D2): 204, la fila sigue en la base pero ya no se ve.
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertFalse(Commitment.objects.filter(pk=pk).exists())
        self.assertTrue(Commitment.all_objects.filter(pk=pk).exists())

    # --- 4. Errores: dos 400 (campo y regla) y 404 -----------------------
    def test_400_por_validacion_de_campo(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url('period'),
            {
                'start_date': '2031-01-01', 'end_date': '2031-12-31',
                'computable_days': 100, 'status': 'activo',
                'amber_threshold': '150.00',  # fuera de 0-100
                'collective_threshold': '90.00', 'parameters_version': 1,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('amber_threshold', response.data)

    def test_400_por_regla_de_negocio(self):
        # RN-001: la suma de ponderadores por cargo y periodo no pasa de 100 %.
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url('meta'),
            {
                'position': self.position.pk, 'period': self.period.pk,
                'item_name': 'Excede', 'target_value': '10.00',
                'unit': 'u', 'weight': '95.00',  # ya hay 10 % asignado
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('weight', response.data)

    def test_400_por_relacion_incongruente(self):
        # La delegacion del compromiso debe ser la del responsable.
        otra = Delegation.objects.create(id='DEL-M2', name='Otra', scope='X')
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url('commitment'),
            {
                'delegation': otra.pk, 'responsible': self.employee.pk,
                'origin': 'X', 'requester': 'Y', 'territory': 'Z',
                'due_date': (timezone.localdate() + timedelta(days=5)).isoformat(),
                'support_area': 'A', 'status': 'ingresado', 'observation': '',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('delegation', response.data)

    def test_404_por_id_inexistente_en_los_6_recursos(self):
        self.client.force_authenticate(self.admin)
        for name in TODOS:
            with self.subTest(recurso=name):
                self.assertEqual(self.client.get(self.missing_url(name)).status_code, 404)

    def test_409_al_borrar_con_datos_asociados(self):
        # El periodo tiene metas y actividades (PROTECT): no se puede borrar.
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail_url('period'))
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Period.objects.filter(pk=self.period.pk).exists())

    # --- 5. Paginacion con >= 60 filas -----------------------------------
    def _crear_filas(self, name):
        """Deja PAGE_ROWS filas del recurso (contando la base)."""
        extra = PAGE_ROWS - 1
        if name == 'activity':
            for i in range(extra):
                self.make_activity(f'Actividad {i}')
        elif name == 'commitment':
            for i in range(extra):
                self.make_commitment(f'Origen {i}')
        elif name == 'meta':
            for i in range(extra):
                self.make_meta(f'Meta {i}', weight='0.10')
        elif name == 'period':
            for i in range(extra):
                Period.objects.create(
                    start_date=date(1900 + i, 1, 1), end_date=date(1900 + i, 12, 31),
                    computable_days=100, status='cerrado',
                    amber_threshold=Decimal('80.00'),
                    collective_threshold=Decimal('90.00'),
                )
        elif name in ('evidence', 'validation'):
            for i in range(extra):
                evidence = Evidence.objects.create(
                    activity=self.activity, file=_png_file(),
                    date=date(2026, 8, 11),
                )
                if name == 'validation':
                    Validation.objects.create(
                        evidence=evidence, employee=self.employee,
                        decision='aprobada', date=date(2026, 8, 12), result=True,
                    )

    def _ids(self, response):
        return [row.get('id', row.get('code')) for row in response.data['results']]

    def test_paginacion_en_los_6_recursos(self):
        self.client.force_authenticate(self.operador)
        for name in TODOS:
            self._crear_filas(name)
            with self.subTest(recurso=name):
                page1 = self.client.get(self.list_url(name))
                self.assertEqual(page1.status_code, 200)
                self.assertGreaterEqual(page1.data['count'], PAGE_ROWS)
                # Nunca devuelve todas las filas en una sola respuesta.
                self.assertEqual(len(page1.data['results']), 25)
                self.assertLess(len(page1.data['results']), page1.data['count'])
                self.assertIsNotNone(page1.data['next'])
                self.assertIsNone(page1.data['previous'])

                page2 = self.client.get(self.list_url(name), {'page': 2})
                self.assertEqual(page2.status_code, 200)
                self.assertEqual(page2.data['count'], page1.data['count'])
                self.assertTrue(page2.data['results'])
                self.assertFalse(set(self._ids(page1)) & set(self._ids(page2)))

    def test_page_size_tiene_tope_de_100(self):
        self.client.force_authenticate(self.operador)
        self._crear_filas('period')
        response = self.client.get(self.list_url('period'), {'page_size': 1000})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data['results']), 100)
