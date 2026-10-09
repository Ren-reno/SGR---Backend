"""Pruebas de los permisos por rol de la API (Evaluación Sumativa 3).

Todavía no hay recursos reales protegidos, así que se prueban con una vista de
prueba que NO declara permission_classes: hereda solo el permiso por defecto de
settings.REST_FRAMEWORK. Reproducen la matriz de la rúbrica:

    sin token                 -> 401
    autenticado sin rol       -> 403 (ni consulta ni modifica)
    api_operador              -> solo lectura (escribir da 403)
    api_admin                 -> lectura y escritura
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import override_settings
from django.urls import include, path, reverse
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from api.permissions import GROUP_API_ADMIN, GROUP_API_OPERADOR

User = get_user_model()

# Credencial ficticia, solo para estas pruebas.
PASSWORD = 'Clave-Prueba-2026!'

SAFE = ('get', 'head', 'options')
WRITE = ('post', 'put', 'patch', 'delete')
# Estado que devuelve ProbeView cuando el permiso deja pasar cada método.
ALLOWED = {
    'get': 200, 'head': 200, 'options': 200,
    'post': 201, 'put': 200, 'patch': 200, 'delete': 204,
}


class ProbeView(APIView):
    """Vista de prueba con todos los métodos y sin permission_classes propios:
    hereda el permiso por defecto de la API."""

    def get(self, request):
        return Response({'ok': True})

    def post(self, request):
        return Response({'ok': True}, status=201)

    def put(self, request):
        return Response({'ok': True})

    def patch(self, request):
        return Response({'ok': True})

    def delete(self, request):
        return Response(status=204)


# URLconf mínimo de RoleMatrixTests (incluye los endpoints de token reales).
urlpatterns = [
    path('probe/', ProbeView.as_view()),
    path('api/', include('api.urls')),
]


@override_settings(ROOT_URLCONF='api.tests_permissions')
class RoleMatrixTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        admin_group = Group.objects.create(name=GROUP_API_ADMIN)
        operador_group = Group.objects.create(name=GROUP_API_OPERADOR)

        def make(username, groups=(), **extra):
            user = User.objects.create_user(
                username=username, password=PASSWORD, **extra)
            user.groups.add(*groups)
            return user

        cls.admin = make('t_admin', [admin_group])
        cls.operador = make('t_operador', [operador_group])
        cls.sin_rol = make('t_sin_rol')
        cls.ambos = make('t_ambos', [admin_group, operador_group])
        cls.superusuario = make('t_superusuario', is_staff=True,
                                is_superuser=True)

    # -- ayudas ---------------------------------------------------------
    def as_user(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(user)}')

    def statuses(self, methods):
        return {m: getattr(self.client, m)('/probe/').status_code
                for m in methods}

    # -- la matriz de la rúbrica ----------------------------------------
    def test_anonymous_gets_401_on_every_method(self):
        for method in SAFE + WRITE:
            with self.subTest(method=method):
                res = getattr(self.client, method)('/probe/')
                self.assertEqual(res.status_code, 401)
                self.assertTrue(res['WWW-Authenticate'].startswith('Bearer'))

    def test_user_without_role_is_denied_everything(self):
        # Autenticado, pero sin rol de la API: ni consulta ni modifica.
        self.as_user(self.sin_rol)
        self.assertEqual(
            self.statuses(SAFE + WRITE), {m: 403 for m in SAFE + WRITE})

    def test_operador_is_read_only(self):
        self.as_user(self.operador)
        self.assertEqual(self.statuses(SAFE), {m: 200 for m in SAFE})
        self.assertEqual(self.statuses(WRITE), {m: 403 for m in WRITE})

    def test_admin_can_use_every_method(self):
        self.as_user(self.admin)
        self.assertEqual(self.statuses(SAFE + WRITE), ALLOWED)

    def test_denied_responses_are_json(self):
        self.as_user(self.operador)
        res = self.client.post('/probe/')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res['Content-Type'], 'application/json')
        self.assertIn('detail', res.json())

    # -- casos límite ---------------------------------------------------
    def test_admin_prevails_when_a_user_has_both_roles(self):
        self.as_user(self.ambos)
        self.assertEqual(self.statuses(SAFE + WRITE), ALLOWED)

    def test_superuser_has_no_implicit_access(self):
        # Sin atajo: ser superusuario no sustituye a pertenecer a un grupo.
        self.as_user(self.superusuario)
        self.assertEqual(
            self.statuses(('get', 'post')), {'get': 403, 'post': 403})

    def test_web_groups_do_not_grant_api_access(self):
        # Los grupos de la aplicación web no son roles de la API.
        for name in ('Administrador', 'Funcionario', 'Verificador'):
            with self.subTest(group=name):
                group, _ = Group.objects.get_or_create(name=name)
                user = User.objects.create_user(
                    username=f't_web_{name.lower()}', password=PASSWORD)
                user.groups.add(group)
                self.as_user(user)
                self.assertEqual(
                    self.statuses(('get', 'post')), {'get': 403, 'post': 403})

    def test_user_deactivated_after_login_gets_401(self):
        # Una cuenta desactivada deja de autenticarse aunque conserve su token
        # y siga en api_admin: 401, no 403.
        self.as_user(self.admin)
        self.assertEqual(self.client.get('/probe/').status_code, 200)
        self.admin.is_active = False
        self.admin.save()
        self.assertEqual(
            self.statuses(('get', 'post')), {'get': 401, 'post': 401})

    def test_removing_the_role_revokes_access_immediately(self):
        # El rol se consulta en cada solicitud: no queda guardado en el token.
        self.as_user(self.admin)
        self.assertEqual(self.client.post('/probe/').status_code, 201)
        self.admin.groups.clear()
        self.assertEqual(self.client.post('/probe/').status_code, 403)
        self.assertEqual(self.client.get('/probe/').status_code, 403)

    # -- de punta a punta, con tokens pedidos al endpoint real ----------
    def test_end_to_end_through_the_token_endpoint(self):
        # Mismo recorrido que la colección de Apidog: pedir el token y usarlo.
        # (identidad, estado esperado de GET, estado esperado de POST)
        expected = [
            (self.admin, 200, 201),
            (self.operador, 200, 403),
            (self.sin_rol, 403, 403),
        ]
        for user, get_status, post_status in expected:
            with self.subTest(user=user.username):
                self.client.credentials()
                res = self.client.post(
                    reverse('api:token_obtain_pair'),
                    {'username': user.username, 'password': PASSWORD},
                    format='json')
                # Aun sin rol se puede obtener token: el rol limita los
                # recursos, no el inicio de sesión.
                self.assertEqual(res.status_code, 200)
                self.client.credentials(
                    HTTP_AUTHORIZATION=f"Bearer {res.json()['access']}")
                self.assertEqual(
                    self.client.get('/probe/').status_code, get_status)
                self.assertEqual(
                    self.client.post('/probe/').status_code, post_status)

    def test_token_refresh_is_public_for_a_user_without_role(self):
        res = self.client.post(
            reverse('api:token_obtain_pair'),
            {'username': 't_sin_rol', 'password': PASSWORD}, format='json')
        self.client.credentials()
        res = self.client.post(
            reverse('api:token_refresh'),
            {'refresh': res.json()['refresh']}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.json())
