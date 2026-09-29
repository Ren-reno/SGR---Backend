import re

from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.exceptions import ValidationError


class SpanishMinimumLengthValidator(MinimumLengthValidator):
    """`MinimumLengthValidator` de Django con los mensajes en español.

    Hereda TODA la lógica (`validate`, el código de error, `min_length`):
    solo se sobreescriben los dos métodos que producen texto. Existe porque
    el proyecto corre con LANGUAGE_CODE='en-us' (cambiarlo afectaría al Admin
    entero y no es alcance de esta fase) y, sin esto, el mensaje de largo
    saldría en inglés junto a los de complejidad, que están en español.
    """

    def get_error_message(self):
        return (
            f'La contraseña es muy corta: debe tener al menos '
            f'{self.min_length} caracteres.'
        )

    def get_help_text(self):
        return f'Debe tener al menos {self.min_length} caracteres.'


class PasswordComplexityValidator:
    """Validador de complejidad para `AUTH_PASSWORD_VALIDATORS`
    (Fase 4, paso 4.4; requisito 4 de la rúbrica formativa).

    Exige al menos una mayúscula, una minúscula, un número y un carácter
    especial. NO valida el largo: eso lo hace `MinimumLengthValidator` de
    Django (min_length=10 en settings), para que haya una sola fuente de
    verdad y el usuario no vea el mismo error duplicado.

    Se registra en settings como validador de Django, así que lo aplica
    `validate_password()` en cualquier flujo que lo use (recuperación de
    contraseña y también el Admin) sin repetir reglas en cada vista.

    Reporta TODAS las reglas incumplidas de una vez (Django junta los
    ValidationError), en vez de mostrar una por intento.
    """

    def validate(self, password, user=None):
        errors = []

        if not re.search(r'[A-Z]', password):
            errors.append(ValidationError(
                'La contraseña debe incluir al menos una letra mayúscula.',
                code='password_no_upper',
            ))
        if not re.search(r'[a-z]', password):
            errors.append(ValidationError(
                'La contraseña debe incluir al menos una letra minúscula.',
                code='password_no_lower',
            ))
        if not re.search(r'\d', password):
            errors.append(ValidationError(
                'La contraseña debe incluir al menos un número.',
                code='password_no_digit',
            ))
        # "Especial" = ni letra, ni número, ni espacio. `\w` incluye el
        # guion bajo como alfanumérico, así que se agrega aparte para que
        # cuente como especial.
        if not re.search(r'[^\w\s]|_', password):
            errors.append(ValidationError(
                'La contraseña debe incluir al menos un carácter especial '
                '(por ejemplo: ! @ # $ % & * . -).',
                code='password_no_special',
            ))

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            'Debe incluir al menos una mayúscula, una minúscula, un número '
            'y un carácter especial.'
        )
