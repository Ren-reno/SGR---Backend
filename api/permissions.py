"""Permisos por rol de la API (Evaluación Sumativa 3).

Los roles se modelan con grupos de Django. Son grupos propios de la API: no se
reutilizan los de la aplicación web (Administrador, Funcionario, Verificador,
...), cuyos permisos son otros.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

GROUP_API_ADMIN = 'api_admin'
GROUP_API_OPERADOR = 'api_operador'


class ApiRolePermission(BasePermission):
    """Matriz de acceso de la API.

        Identidad                      GET/HEAD/OPTIONS   POST/PUT/PATCH/DELETE
        Sin token o token inválido     401                401
        Autenticado sin rol de la API  403                403
        Grupo api_operador             permitido          403
        Grupo api_admin                permitido          permitido

    - Sin atajo para superusuarios: ser ``is_superuser`` no da acceso a la API;
      hay que pertenecer a uno de los dos grupos.
    - Si un usuario está en ambos grupos, prevalece api_admin.
    - Es el permiso por defecto de DRF (settings.REST_FRAMEWORK), así que falla
      cerrado: toda vista nueva queda protegida por rol salvo que declare otra
      cosa. Los endpoints de token de Simple JWT son públicos por definición.
    - El 401 (en vez de 403) para quien no se autenticó lo decide DRF, porque
      JWTAuthentication define la cabecera ``WWW-Authenticate``.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        roles = set(
            user.groups.filter(
                name__in=(GROUP_API_ADMIN, GROUP_API_OPERADOR),
            ).values_list('name', flat=True)
        )
        if GROUP_API_ADMIN in roles:
            return True
        if GROUP_API_OPERADOR in roles:
            return request.method in SAFE_METHODS
        return False
