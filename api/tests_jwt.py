"""Pruebas de autenticación JWT de la API (Evaluación Sumativa 3).

Cubre los dos endpoints de token (`/api/token/` y `/api/token/refresh/`) y la
configuración global de DRF: JWT como único autenticador, de modo que una
solicitud sin token (o con un token inválido) recibe 401 -no 403- y que todas
las respuestas son JSON.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import path, reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()

# Credenciales ficticias, solo para estas pruebas.
PASSWORD = 'Clave-Prueba-2026!'


class ProbeView(APIView):
    """Vista de prueba que usa SOLO los valores por defecto de DRF
    (autenticación, permisos y renderers de settings.REST_FRAMEWORK)."""

    def get(self, request):
        return Response({'username': request.user.get_username()})


# URLconf mínimo de GlobalDefaultsTests: no existe ningún recurso protegido
# todavía, así que se prueba la configuración global con esta vista.
urlpatterns = [path('probe/', ProbeView.as_view())]


class TokenObtainTests(APITestCase):
    """POST /api/token/"""

    @classmethod
    def setUpTestData(cls):
        # Usuarios normales: ni staff ni superusuario.
        cls.user = User.objects.create_user(
            username='api_tester', password=PASSWORD)
        cls.inactive = User.objects.create_user(
            username='api_inactive', password=PASSWORD, is_active=False)
        cls.url = reverse('api:token_obtain_pair')

    def obtain(self, username, password):
        return self.client.post(
            self.url, {'username': username, 'password': password},
            format='json')

    def test_valid_credentials_return_access_and_refresh(self):
        res = self.obtain('api_tester', PASSWORD)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/json')
        self.assertEqual(set(res.json()), {'access', 'refresh'})
        access = AccessToken(res.json()['access'])
        refresh = RefreshToken(res.json()['refresh'])
        self.assertEqual(access['token_type'], 'access')
        self.assertEqual(refresh['token_type'], 'refresh')
        self.assertEqual(str(access['user_id']), str(self.user.pk))
        self.assertEqual(str(refresh['user_id']), str(self.user.pk))

    def test_token_lifetimes_follow_settings(self):
        res = self.obtain('api_tester', PASSWORD)
        access = AccessToken(res.json()['access'])
        refresh = RefreshToken(res.json()['refresh'])
        self.assertEqual(
            access['exp'] - access['iat'],
            int(jwt_settings.ACCESS_TOKEN_LIFETIME.total_seconds()))
        self.assertEqual(
            refresh['exp'] - refresh['iat'],
            int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()))

    def test_wrong_password_returns_401(self):
        res = self.obtain('api_tester', 'otra-clave-incorrecta')
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res['Content-Type'], 'application/json')
        self.assertIn('detail', res.json())
        self.assertNotIn('access', res.json())
        self.assertNotIn('refresh', res.json())

    def test_unknown_user_returns_401(self):
        res = self.obtain('no_existe', PASSWORD)
        self.assertEqual(res.status_code, 401)
        self.assertNotIn('access', res.json())

    def test_inactive_user_returns_401(self):
        # Credenciales correctas, pero la cuenta está desactivada.
        res = self.obtain('api_inactive', PASSWORD)
        self.assertEqual(res.status_code, 401)
        self.assertNotIn('access', res.json())

    def test_missing_fields_return_400(self):
        res = self.client.post(self.url, {}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('username', res.json())
        self.assertIn('password', res.json())

    def test_get_is_not_allowed(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 405)
        self.assertEqual(res['Content-Type'], 'application/json')


class TokenRefreshTests(APITestCase):
    """POST /api/token/refresh/"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='api_tester', password=PASSWORD)
        cls.obtain_url = reverse('api:token_obtain_pair')
        cls.refresh_url = reverse('api:token_refresh')

    def tokens(self):
        res = self.client.post(
            self.obtain_url,
            {'username': 'api_tester', 'password': PASSWORD}, format='json')
        self.assertEqual(res.status_code, 200)
        return res.json()

    def test_valid_refresh_returns_a_new_access_token(self):
        tokens = self.tokens()
        res = self.client.post(
            self.refresh_url, {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/json')
        # No se rota el refresh: la respuesta trae solo un access nuevo.
        self.assertEqual(set(res.json()), {'access'})
        access = AccessToken(res.json()['access'])
        self.assertEqual(access['token_type'], 'access')
        self.assertEqual(str(access['user_id']), str(self.user.pk))

    def test_invalid_refresh_returns_401(self):
        res = self.client.post(
            self.refresh_url, {'refresh': 'esto-no-es-un-token'},
            format='json')
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()['code'], 'token_not_valid')

    def test_access_token_is_rejected_as_refresh(self):
        tokens = self.tokens()
        res = self.client.post(
            self.refresh_url, {'refresh': tokens['access']}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_missing_refresh_returns_400(self):
        res = self.client.post(self.refresh_url, {}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('refresh', res.json())

    def test_refresh_of_a_user_deactivated_afterwards_returns_401(self):
        tokens = self.tokens()
        self.user.is_active = False
        self.user.save()
        res = self.client.post(
            self.refresh_url, {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(res.status_code, 401)


@override_settings(ROOT_URLCONF='api.tests_jwt')
class GlobalDefaultsTests(APITestCase):
    """Configuración global de DRF, probada con ProbeView."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='api_tester', password=PASSWORD)

    def bearer(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_no_token_returns_401_with_bearer_challenge(self):
        res = self.client.get('/probe/')
        self.assertEqual(res.status_code, 401)
        self.assertTrue(res['WWW-Authenticate'].startswith('Bearer'))
        self.assertEqual(res['Content-Type'], 'application/json')

    def test_valid_access_token_is_accepted(self):
        self.bearer(AccessToken.for_user(self.user))
        res = self.client.get('/probe/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {'username': 'api_tester'})

    def test_garbage_token_returns_401(self):
        self.bearer('esto-no-es-un-token')
        self.assertEqual(self.client.get('/probe/').status_code, 401)

    def test_expired_access_token_returns_401(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(from_time=timezone.now(), lifetime=timedelta(seconds=-60))
        self.bearer(token)
        self.assertEqual(self.client.get('/probe/').status_code, 401)

    def test_refresh_token_is_not_accepted_as_access(self):
        self.bearer(RefreshToken.for_user(self.user))
        self.assertEqual(self.client.get('/probe/').status_code, 401)

    def test_token_of_an_inactive_user_returns_401(self):
        token = AccessToken.for_user(self.user)
        self.user.is_active = False
        self.user.save()
        self.bearer(token)
        self.assertEqual(self.client.get('/probe/').status_code, 401)

    def test_web_session_is_not_accepted(self):
        # Sin SessionAuthentication, estar logueado en la web no autentica en
        # la API: sin token sigue siendo 401 (no 200, no 403).
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/probe/').status_code, 401)

    def test_html_browsable_api_is_not_exposed(self):
        # Renderer solo JSON: pedir HTML no devuelve la página de DRF.
        res = self.client.get('/probe/', HTTP_ACCEPT='text/html')
        self.assertEqual(res.status_code, 406)
