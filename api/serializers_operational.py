from rest_framework import serializers

from performance.models import Evidence, Validation


class EvidenceSerializer(serializers.ModelSerializer):
    """Evidence (solo lectura): campos explicitos. `file` sale como URL
    absoluta de lectura (DRF la arma con el request del contexto)."""

    class Meta:
        model = Evidence
        fields = [
            'code',
            'activity',
            'file',
            'date',
            'metadata',
            'review_status',
        ]
        read_only_fields = fields


class ValidationSerializer(serializers.ModelSerializer):
    """Validation (solo lectura): historial de revision de una evidencia."""

    class Meta:
        model = Validation
        fields = [
            'id',
            'evidence',
            'employee',
            'decision',
            'date',
            'notes',
            'result',
            'version',
        ]
        read_only_fields = fields