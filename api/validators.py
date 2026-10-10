from rest_framework import serializers

from performance.forms import _MIN_PHONE_DIGITS, _PHONE_CHARS


def validate_phone(value):
    if not value:
        return value
    if not _PHONE_CHARS.match(value):
        raise serializers.ValidationError(
            "El teléfono solo puede contener dígitos, +, (, ), - y espacios."
        )
    if sum(c.isdigit() for c in value) < _MIN_PHONE_DIGITS:
        raise serializers.ValidationError(
            f"El teléfono debe tener al menos {_MIN_PHONE_DIGITS} dígitos."
        )
    return value