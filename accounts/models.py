from django.db import models  # noqa: F401

# App creada por la Decisión 13 (docs/decisiones.md) para separar
# responsabilidades de acceso: login, logout y recuperación de contraseña
# con código numérico de 6 dígitos.
#
# Sin modelos todavía a propósito -- esta pieza queda asignada como trabajo
# aparte de los 8 módulos (ver Decisión 13). Cuando se construya, el modelo
# del código de recuperación (algo como PasswordResetCode: user, code,
# created_at, used_at) y las vistas de login/logout/recuperación viven acá.
