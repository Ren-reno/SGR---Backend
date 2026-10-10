from rest_framework import viewsets

from performance.models import Activity

from .serializers import ActivitySerializer


class ActivityViewSet(viewsets.ModelViewSet):
    """CRUD de Activity. Eliminacion logica (D2): DELETE responde 204 y la
    actividad deja de listarse; si tiene evidencias, responde 409.

    Permisos: heredados de ApiRolePermission (settings.REST_FRAMEWORK).
    """

    serializer_class = ActivitySerializer
    queryset = (
        Activity.objects
        .select_related('employee', 'period', 'meta', 'attention')
        .order_by('id')
    )

    def perform_destroy(self, instance):
        instance.soft_delete()