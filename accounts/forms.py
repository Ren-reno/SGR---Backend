import hmac

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import PasswordResetCode

User = get_user_model()


class LoginForm(AuthenticationForm):
    """Login con `django.contrib.auth` (paso 4.2). Se hereda de
    AuthenticationForm -- que ya valida credenciales con `authenticate()`
    y rechaza usuarios inactivos -- solo para poner etiquetas en español
    y clases CSS. No se reescribe la autenticación."""

    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}),
    )
    password = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )


class ForgotPasswordForm(forms.Form):
    """Paso 1 de la recuperación: identificar al usuario (paso 4.3)."""

    username = forms.CharField(
        label='Usuario',
        max_length=150,
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}),
    )


class ResetPasswordForm(forms.Form):
    """Paso 2 de la recuperación: código + nueva contraseña dos veces
    (paso 4.4).

    Decisiones de seguridad (están acá y no en la vista para que un solo
    lugar concentre la regla y se pueda probar sin HTTP):

    1. `clean()` hace UNA verificación del par (usuario, código) y, si algo
       falla, devuelve siempre el mismo mensaje genérico. No distingue
       "el usuario no existe" de "el código es incorrecto" de "el código
       venció" de "el código ya se usó": decirlo permitiría a un atacante
       enumerar cuentas o saber que acertó el usuario y le falta el código.

    2. Cada código incorrecto suma un intento fallido al código vigente del
       usuario (`register_failed_attempt`); al llegar a MAX_ATTEMPTS queda
       bloqueado. Sin este tope, 10**6 combinaciones se agotan por fuerza
       bruta. Los intentos se cuentan contra el código y no contra la IP
       porque no depende de infraestructura ni de un cache externo.

    3. La contraseña se valida con `validate_password()` (mecanismo estándar
       de Django) contra AUTH_PASSWORD_VALIDATORS, que incluye el validador
       de complejidad propio. Solo se valida cuando el código ya fue
       aceptado: no se malgasta un intento en el código ni se hace trabajo
       de validación para alguien que no ha probado ser el dueño.
    """

    GENERIC_ERROR = (
        'El usuario o el código no son válidos, o el código ya venció. '
        'Vuelve a solicitar uno nuevo.'
    )

    username = forms.CharField(
        label='Usuario',
        max_length=150,
        widget=forms.TextInput(attrs={'autocomplete': 'username'}),
    )
    code = forms.CharField(
        label='Código de 6 dígitos',
        min_length=PasswordResetCode.CODE_LENGTH,
        max_length=PasswordResetCode.CODE_LENGTH,
        widget=forms.TextInput(attrs={
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': r'\d{6}',
        }),
    )
    new_password1 = forms.CharField(
        label='Nueva contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label='Repite la nueva contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def clean_code(self):
        code = self.cleaned_data['code'].strip()
        if not (code.isascii() and code.isdigit()):
            raise ValidationError('El código son 6 dígitos numéricos.')
        return code

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username')
        code = cleaned.get('code')
        pw1 = cleaned.get('new_password1')
        pw2 = cleaned.get('new_password2')

        # Si faltan campos, Django ya marcó sus errores individuales.
        if not (username and code and pw1 and pw2):
            return cleaned

        # -- 1) Verificar el par (usuario, código) --------------------
        # Se busca por `username` exacto (sensible a mayúsculas), el mismo
        # criterio que usa el login de Django.
        user = User.objects.filter(username=username, is_active=True).first()
        reset = None
        if user is not None:
            reset = (
                PasswordResetCode.objects
                .filter(user=user, used_at__isnull=True)
                .order_by('-created_at')
                .first()
            )

        if reset is None or not reset.is_valid:
            raise ValidationError(self.GENERIC_ERROR)

        # Comparación en tiempo constante (evita filtrar por timing cuánto
        # del código coincide).
        if not hmac.compare_digest(reset.code, code):
            reset.register_failed_attempt()
            raise ValidationError(self.GENERIC_ERROR)

        # -- 2) Código aceptado: validar la contraseña ----------------
        if pw1 != pw2:
            self.add_error('new_password2', 'Las contraseñas no coinciden.')
            return cleaned
        try:
            password_validation.validate_password(pw1, user)
        except ValidationError as exc:
            self.add_error('new_password1', exc)
            return cleaned

        self.user = user
        self.reset = reset
        return cleaned

    def save(self):
        """Cambia la contraseña e invalida el código, atómicamente.

        `set_password()` guarda el hash (PBKDF2 por defecto), nunca texto
        plano. `mark_used()` deja el código inservible: un segundo intento
        con el mismo código falla en `clean()` (`used_at` ya no es nulo).
        """
        with transaction.atomic():
            self.user.set_password(self.cleaned_data['new_password1'])
            self.user.save(update_fields=['password'])
            self.reset.mark_used()
        return self.user
