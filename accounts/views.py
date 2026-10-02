from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from .forms import ForgotPasswordForm, LoginForm, ResetPasswordForm
from .models import PasswordResetCode


class SgrLoginView(LoginView):
    """Login con `django.contrib.auth` (paso 4.2).

    `redirect_authenticated_user=True`: quien ya tiene sesión no vuelve a ver
    el formulario. El destino tras entrar es `settings.LOGIN_REDIRECT_URL`,
    o el `?next=` que puso `@login_required` -- Django valida que ese `next`
    sea del mismo host (no hay open redirect).
    """
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class SgrLogoutView(LogoutView):
    """Logout (paso 4.2). Desde Django 5.0 solo acepta POST, así que no se
    puede cerrar la sesión de alguien con un simple enlace o <img> ajeno;
    el template lo envía con un formulario + CSRF."""
    next_page = reverse_lazy('accounts:login')


class ForgotPasswordView(View):
    """Paso 1 de la recuperación (paso 4.3): generar el código.

    Responde IGUAL exista o no el usuario -- así este formulario no sirve
    para averiguar qué cuentas existen (enumeración de usuarios).

    Corrección (Ing. Software, observación del docente): el código YA NO se
    muestra nunca en la respuesta HTTP, ni siquiera con DEBUG=True -- se
    "envía" como correo con send_mail(). Con EMAIL_BACKEND de consola
    (settings.py), el contenido completo del correo aparece en el log del
    servidor (terminal de runserver en desarrollo, `journalctl -u sgr -f`
    en el despliegue de AWS), nunca en la pantalla del usuario. No requiere
    SMTP real ni cuenta de correo verdadera -- sigue siendo apto para la
    demo sin configurar un servidor de correo.
    """
    template_name = 'accounts/forgot_password.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ForgotPasswordForm()})

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        username = form.cleaned_data['username']
        user = get_user_model().objects.filter(
            username=username, is_active=True
        ).first()

        if user is not None:
            reset = PasswordResetCode.issue_for(user)
            send_mail(
                subject='SGR — Código de recuperación de contraseña',
                message=(
                    f'Hola {user.get_username()},\n\n'
                    f'Tu código de recuperación es: {reset.code}\n'
                    f'Válido por {PasswordResetCode.CODE_TTL_MINUTES} minutos.\n\n'
                    'Si no solicitaste este código, ignora este mensaje.'
                ),
                from_email=None,  # usa settings.DEFAULT_FROM_EMAIL
                recipient_list=[user.email or f'{user.get_username()}@demo.local'],
                fail_silently=True,
            )

        # Mismo mensaje en ambos casos, exista o no el usuario (sigue sin
        # permitir enumeración de cuentas).
        messages.info(
            request,
            'Si el usuario existe, se envió un código de 6 dígitos válido '
            f'por {PasswordResetCode.CODE_TTL_MINUTES} minutos a su correo '
            'registrado.',
        )
        return render(request, 'accounts/forgot_password_done.html', {
            'username': username,
            'ttl_minutes': PasswordResetCode.CODE_TTL_MINUTES,
        })


class ResetPasswordView(View):
    """Paso 2 de la recuperación (paso 4.4): código + contraseña nueva."""
    template_name = 'accounts/reset_password.html'

    def get(self, request):
        initial = {}
        if request.GET.get('username'):
            initial['username'] = request.GET['username']
        return render(request, self.template_name,
                      {'form': ResetPasswordForm(initial=initial)})

    def post(self, request):
        form = ResetPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        form.save()
        messages.success(
            request,
            'Contraseña actualizada. Ya puedes iniciar sesión con la nueva.',
        )
        return redirect('accounts:login')
