import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class PasswordResetCode(models.Model):

    CODE_LENGTH = 6
    CODE_TTL_MINUTES = 10
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_codes',
    )
    code = models.CharField(max_length=CODE_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user} — {self.status}'

    # ---- Generación -----------------------------------------------------

    @classmethod
    def generate_code(cls):
        """6 dígitos con ceros a la izquierda permitidos ('004217')."""
        return f'{secrets.randbelow(10 ** cls.CODE_LENGTH):0{cls.CODE_LENGTH}d}'

    @classmethod
    def issue_for(cls, user):
        """Crea un código nuevo e invalida los pendientes del usuario.

        Se "invalida" marcando `used_at`: es el mismo estado terminal que un
        código consumido, así que no hace falta otra columna.
        """
        now = timezone.now()
        cls.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
        return cls.objects.create(
            user=user,
            code=cls.generate_code(),
            expires_at=now + timedelta(minutes=cls.CODE_TTL_MINUTES),
        )

    # ---- Estado ---------------------------------------------------------

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_locked(self):
        return self.failed_attempts >= self.MAX_ATTEMPTS

    @property
    def is_valid(self):
        """Vivo = no usado, no vencido y con intentos disponibles."""
        return (
            self.used_at is None
            and not self.is_expired
            and not self.is_locked
        )

    @property
    def status(self):
        """Texto legible para el Admin."""
        if self.used_at is not None:
            return 'usado/invalidado'
        if self.is_expired:
            return 'vencido'
        if self.is_locked:
            return 'bloqueado'
        return 'vigente'

    # ---- Consumo --------------------------------------------------------

    def register_failed_attempt(self):
        self.failed_attempts += 1
        self.save(update_fields=['failed_attempts'])

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


class LoginAttempt(models.Model):
    """Bloqueo temporal tras intentos fallidos de inicio de sesión
    (Ing. Software, hallazgo del docente: el login no tenía límite de
    intentos, a diferencia de PasswordResetCode que sí lo tiene).

    Mismo patrón que PasswordResetCode (contador + bloqueo), adaptado:
    acá no hay "código" que vencer, así que el bloqueo es temporal
    (LOCKOUT_MINUTES) en vez de permanente hasta pedir uno nuevo. Se
    cuenta por usuario, no por IP: no depende de infraestructura ni de
    un cache externo, igual que PasswordResetCode.

    Una fila por usuario (OneToOne): se crea la primera vez que alguien
    falla al iniciar sesión con ese username, y se reutiliza en adelante.
    """

    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 10

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='login_attempt',
    )
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.user} — {self.failed_attempts} intento(s) fallido(s)'

    @property
    def is_locked(self):
        return self.locked_until is not None and timezone.now() < self.locked_until

    def register_failure(self):
        self.failed_attempts += 1
        if self.failed_attempts >= self.MAX_ATTEMPTS:
            self.locked_until = timezone.now() + timedelta(minutes=self.LOCKOUT_MINUTES)
        self.save(update_fields=['failed_attempts', 'locked_until'])

    def reset(self):
        self.failed_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_attempts', 'locked_until'])

    @classmethod
    def get_or_create_for(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj