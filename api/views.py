from rest_framework import viewsets

from performance import models as perf_models
from performance.models import Activity, Commitment

from .serializers import (
    ActivitySerializer,
    CommitmentSerializer,
    MetaSerializer,
    PeriodSerializer,
)


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


class CommitmentViewSet(viewsets.ModelViewSet):
    """CRUD de Commitment. Eliminacion logica (D2): DELETE responde 204 y el
    compromiso deja de listarse.

    Permisos: heredados de ApiRolePermission (settings.REST_FRAMEWORK).
    """

    serializer_class = CommitmentSerializer
    queryset = (
        Commitment.objects
        .select_related('delegation', 'responsible')
        .order_by('id')
    )

    def perform_destroy(self, instance):
        instance.soft_delete()


class MetaViewSet(viewsets.ModelViewSet):
    """CRUD de Meta. Eliminacion fisica (D2): DELETE responde 204; si la meta
    tiene actividades asociadas (PROTECT), responde 409.

    Permisos: heredados de ApiRolePermission (settings.REST_FRAMEWORK).
    """

    serializer_class = MetaSerializer
    queryset = (
        perf_models.Meta.objects
        .select_related('position', 'period')
        .order_by('id')
    )


class PeriodViewSet(viewsets.ModelViewSet):
    """CRUD de Period. Eliminacion fisica (D2): DELETE responde 204; si el
    periodo tiene metas o actividades asociadas (PROTECT), responde 409.

    Permisos: heredados de ApiRolePermission (settings.REST_FRAMEWORK).
    """

    serializer_class = PeriodSerializer
    queryset = perf_models.Period.objects.order_by('id')
