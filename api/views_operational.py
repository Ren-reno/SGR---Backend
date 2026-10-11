from rest_framework import viewsets

from performance.models import Evidence, Validation

from .serializers_operational import EvidenceSerializer, ValidationSerializer


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    """Evidence: solo lista y detalle. El identificador es `code`
    (EVID-0001), no un numero. `objects` excluye lo eliminado logicamente.

    Permisos: heredados de ApiRolePermission (settings.REST_FRAMEWORK).
    """

    serializer_class = EvidenceSerializer
    lookup_field = 'code'
    queryset = Evidence.objects.select_related('activity').order_by('code')


class ValidationViewSet(viewsets.ReadOnlyModelViewSet):
    """Validation: solo lista y detalle. Una validacion eliminada
    logicamente no aparece.

    Permisos: heredados de ApiRolePermission (settings.REST_FRAMEWORK).
    """

    serializer_class = ValidationSerializer
    queryset = (
        Validation.objects
        .select_related('evidence', 'employee')
        .order_by('id')
    )