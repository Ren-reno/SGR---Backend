from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import PasswordResetCode

User = get_user_model()

OLD_PW = 'ClaveAntigua#2026'
NEW_PW = 'NuevaClave#2026x'


def make_user(username='ana', password=OLD_PW, **extra):
    return User.objects.create_user(username=username, password=password, **extra)


# ---------------------------------------------------------------------------
# Modelo PasswordResetCode (paso 4.1)
# ---------------------------------------------------------------------------
class PasswordResetCodeModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_code_is_six_digits_numeric(self):
        for _ in range(200):
            code = PasswordResetCode.generate_code()
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())

    def test_issue_creates_valid_code_with_expiry(self):
        reset = PasswordResetCode.issue_for(self.user)
        self.assertTrue(reset.is_valid)
        self.assertEqual(reset.status, 'vigente')
        delta = reset.expires_at - reset.created_at
        self.assertAlmostEqual(
            delta.total_seconds(),
            PasswordResetCode.CODE_TTL_MINUTES * 60, delta=5)

    def test_expired_code_is_not_valid(self):
        reset = PasswordResetCode.issue_for(self.user)
        reset.expires_at = timezone.now() - timedelta(seconds=1)
        reset.save()
        self.assertFalse(reset.is_valid)
        self.assertEqual(reset.status, 'vencido')

    def test_new_code_invalidates_previous_ones(self):
        first = PasswordResetCode.issue_for(self.user)
        second = PasswordResetCode.issue_for(self.user)
        first.refresh_from_db()
        self.assertFalse(first.is_valid)
        self.assertTrue(second.is_valid)
        self.assertEqual(
            PasswordResetCode.objects.filter(
                user=self.user, used_at__isnull=True).count(), 1)

    def test_locks_after_max_failed_attempts(self):
        reset = PasswordResetCode.issue_for(self.user)
        for _ in range(PasswordResetCode.MAX_ATTEMPTS):
            reset.register_failed_attempt()
        self.assertTrue(reset.is_locked)
        self.assertFalse(reset.is_valid)
        self.assertEqual(reset.status, 'bloqueado')


# ---------------------------------------------------------------------------
# Validador de complejidad (paso 4.4) -- vía validate_password de Django
# ---------------------------------------------------------------------------
class PasswordComplexityTests(TestCase):
    def assertRejected(self, pw, *fragments):
        with self.assertRaises(ValidationError) as ctx:
            validate_password(pw)
        text = ' | '.join(ctx.exception.messages)
        for fragment in fragments:
            self.assertIn(fragment, text)

    def test_valid_password_passes(self):
        validate_password('Segura#Clave2026')  # no lanza

    def test_too_short(self):
        self.assertRejected('Ab1#xyz', 'al menos 10 caracteres')

    def test_missing_uppercase(self):
        self.assertRejected('segura#clave2026', 'mayúscula')

    def test_missing_lowercase(self):
        self.assertRejected('SEGURA#CLAVE2026', 'minúscula')

    def test_missing_digit(self):
        self.assertRejected('Segura#ClaveAbcd', 'número')

    def test_missing_special(self):
        self.assertRejected('SeguraClave2026x', 'especial')

    def test_underscore_counts_as_special(self):
        validate_password('Segura_Clave2026')

    def test_space_alone_is_not_special(self):
        self.assertRejected('Segura Clave 2026', 'especial')

    def test_reports_every_failed_rule_at_once(self):
        self.assertRejected('abcdefghijkl', 'mayúscula', 'número', 'especial')


# ---------------------------------------------------------------------------
# Login / logout (paso 4.2)
# ---------------------------------------------------------------------------
class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_login_page_renders(self):
        res = self.client.get(reverse('accounts:login'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Iniciar sesión')

    def test_login_with_valid_credentials(self):
        res = self.client.post(reverse('accounts:login'),
                               {'username': 'ana', 'password': OLD_PW})
        self.assertRedirects(res, reverse('performance:home'),
                             fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_with_wrong_password_fails(self):
        res = self.client.post(reverse('accounts:login'),
                               {'username': 'ana', 'password': 'incorrecta'})
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        self.client.post(reverse('accounts:login'),
                         {'username': 'ana', 'password': OLD_PW})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_honours_safe_next(self):
        res = self.client.post(
            reverse('accounts:login') + '?next=/admin/',
            {'username': 'ana', 'password': OLD_PW, 'next': '/admin/'})
        self.assertRedirects(res, '/admin/', fetch_redirect_response=False)

    def test_login_rejects_external_next(self):
        """Open redirect: un `next` a otro sitio no debe seguirse."""
        res = self.client.post(
            reverse('accounts:login'),
            {'username': 'ana', 'password': OLD_PW,
             'next': 'https://evil.example.com/'})
        self.assertEqual(res.status_code, 302)
        self.assertNotIn('evil.example.com', res['Location'])

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        res = self.client.get(reverse('accounts:logout'))
        self.assertEqual(res.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_via_post_closes_session(self):
        self.client.force_login(self.user)
        res = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(res, reverse('accounts:login'),
                             fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_has_csrf_protection(self):
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        res = strict.post(reverse('accounts:login'),
                          {'username': 'ana', 'password': OLD_PW})
        self.assertEqual(res.status_code, 403)


# ---------------------------------------------------------------------------
# Recuperación de contraseña, flujo completo (pasos 4.3 y 4.4)
# ---------------------------------------------------------------------------
class ForgotPasswordViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.url = reverse('accounts:forgot_password')

    @override_settings(DEBUG=True)
    def test_debug_true_shows_code_on_screen(self):
        res = self.client.post(self.url, {'username': 'ana'})
        reset = PasswordResetCode.objects.get(user=self.user)
        self.assertContains(res, f'<div class="demo-code">{reset.code}</div>')

    @override_settings(DEBUG=False)
    def test_debug_false_never_leaks_code_in_response(self):
        res = self.client.post(self.url, {'username': 'ana'})
        reset = PasswordResetCode.objects.get(user=self.user)
        self.assertNotContains(res, reset.code)
        self.assertEqual(res.status_code, 200)

    @override_settings(DEBUG=True)
    def test_unknown_user_gets_same_page_and_no_code(self):
        """No revelar si el usuario existe (enumeración de cuentas)."""
        res = self.client.post(self.url, {'username': 'no-existe'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Si el usuario existe')
        self.assertEqual(PasswordResetCode.objects.count(), 0)
        # Se busca el <div> renderizado, no la clase a secas: `.demo-code`
        # también aparece en el CSS de base.html y daría un falso positivo.
        self.assertNotContains(res, '<div class="demo-code">')
        self.assertIsNone(res.context['demo_code'])

    @override_settings(DEBUG=True)
    def test_inactive_user_gets_no_code(self):
        self.user.is_active = False
        self.user.save()
        self.client.post(self.url, {'username': 'ana'})
        self.assertEqual(PasswordResetCode.objects.count(), 0)


@override_settings(DEBUG=True)
class ResetPasswordFlowTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.url = reverse('accounts:reset_password')
        self.reset = PasswordResetCode.issue_for(self.user)

    def payload(self, **over):
        data = {
            'username': 'ana',
            'code': self.reset.code,
            'new_password1': NEW_PW,
            'new_password2': NEW_PW,
        }
        data.update(over)
        return data

    def test_full_flow_end_to_end(self):
        """Solicitar código -> ingresarlo -> nueva contraseña -> login."""
        res = self.client.post(reverse('accounts:forgot_password'),
                               {'username': 'ana'})
        code = PasswordResetCode.objects.filter(
            user=self.user, used_at__isnull=True).get().code
        self.assertContains(res, code)

        res = self.client.post(self.url, self.payload(code=code))
        self.assertRedirects(res, reverse('accounts:login'),
                             fetch_redirect_response=False)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PW))
        self.assertFalse(self.user.check_password(OLD_PW))
        self.assertTrue(
            self.client.login(username='ana', password=NEW_PW))

    def test_password_is_stored_hashed_never_plaintext(self):
        self.client.post(self.url, self.payload())
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, NEW_PW)
        self.assertNotIn(NEW_PW, self.user.password)
        self.assertTrue(self.user.password.startswith('pbkdf2_'))

    def test_code_cannot_be_reused_after_success(self):
        """Requisito explícito de la rúbrica."""
        self.client.post(self.url, self.payload())
        self.reset.refresh_from_db()
        self.assertIsNotNone(self.reset.used_at)

        res = self.client.post(self.url, self.payload(
            new_password1='OtraClave#2027z', new_password2='OtraClave#2027z'))
        self.assertEqual(res.status_code, 200)  # se queda en el formulario
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PW))  # no cambió de nuevo
        self.assertFalse(self.user.check_password('OtraClave#2027z'))

    def test_wrong_code_is_rejected(self):
        wrong = '000000' if self.reset.code != '000000' else '111111'
        res = self.client.post(self.url, self.payload(code=wrong))
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PW))

    def test_expired_code_is_rejected(self):
        self.reset.expires_at = timezone.now() - timedelta(minutes=1)
        self.reset.save()
        res = self.client.post(self.url, self.payload())
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PW))

    def test_passwords_must_match(self):
        res = self.client.post(self.url, self.payload(
            new_password2='Distinta#2026xx'))
        self.assertContains(res, 'no coinciden')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PW))
        self.reset.refresh_from_db()
        self.assertIsNone(self.reset.used_at)  # no se gastó el código

    def test_weak_password_rejected_and_code_not_consumed(self):
        res = self.client.post(self.url, self.payload(
            new_password1='debil', new_password2='debil'))
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PW))
        self.reset.refresh_from_db()
        self.assertIsNone(self.reset.used_at)  # puede reintentar con otra clave

    def test_error_message_is_identical_for_all_failure_causes(self):
        """Mismo mensaje si el usuario no existe, el código es malo, venció
        o ya se usó: no se filtra qué falló."""
        generic = 'El usuario o el código no son válidos'

        unknown = self.client.post(self.url, self.payload(username='fantasma'))
        self.assertContains(unknown, generic)

        wrong_code = '000000' if self.reset.code != '000000' else '111111'
        bad = self.client.post(self.url, self.payload(code=wrong_code))
        self.assertContains(bad, generic)

        self.reset.expires_at = timezone.now() - timedelta(minutes=1)
        self.reset.save()
        expired = self.client.post(self.url, self.payload())
        self.assertContains(expired, generic)

    def test_brute_force_locks_the_code(self):
        """5 fallos bloquean el código: ni el correcto sirve ya."""
        good = self.reset.code
        wrong = '000000' if good != '000000' else '111111'
        for _ in range(PasswordResetCode.MAX_ATTEMPTS):
            self.client.post(self.url, self.payload(code=wrong))
        self.reset.refresh_from_db()
        self.assertTrue(self.reset.is_locked)

        res = self.client.post(self.url, self.payload(code=good))
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PW))

    def test_code_of_another_user_does_not_work(self):
        other = make_user('beto')
        other_reset = PasswordResetCode.issue_for(other)
        res = self.client.post(self.url, self.payload(code=other_reset.code))
        # solo es válido si por casualidad coincide con el de 'ana'
        if other_reset.code != self.reset.code:
            self.assertEqual(res.status_code, 200)
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password(OLD_PW))

    def test_non_numeric_code_rejected(self):
        res = self.client.post(self.url, self.payload(code='12ab56'))
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PW))

    def test_reset_has_csrf_protection(self):
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        res = strict.post(self.url, self.payload())
        self.assertEqual(res.status_code, 403)
