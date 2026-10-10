from django.db.models import ProtectedError, RestrictedError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, (ProtectedError, RestrictedError)):
        return Response(
            {"detail": "No se puede eliminar: el registro tiene datos asociados."},
            status=409,
        )
    return exception_handler(exc, context)