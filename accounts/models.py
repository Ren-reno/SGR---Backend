import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class PasswordResetCode(models.Model):
    """Código numérico de 6 dígitos para recuperar la contraseña
    (Fase 4, paso 4.1; requisito 4 de la rúbrica formativa).

    Reglas de seguridad que este modelo hace cumplir:
    - El código se genera con `secrets` (CSPRNG), nunca con `random`.
    - Vence a los CODE_TTL_MINUTES minutos de creado.
    - Es de un solo uso: `used_at` se llena al consumirse y desde ese
      momento `is_valid` es False ("no puede reutilizarse luego de una
      recuperación exitosa").
    - Limita los intentos fallidos (MAX_ATTEMPTS). Un código de 6 dígitos
      tiene solo 10**6 combinaciones, así que sin este tope se adivinaría
      por fuerza bruta en minutos. Por eso el límite de intentos + la
      expiración corta son la defensa real; hashear el código no aportaría
      nada con un espacio de búsqueda tan chico.
    - Pedir un código nuevo invalida los anteriores del mismo usuario
      (ver `issue_for`), así que nunca hay dos códigos vivos a la vez.
    """

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
