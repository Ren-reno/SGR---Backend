from rest_framework import serializers

from performance.models import Activity

from .mixins import ModelCleanMixin
from .validators import validate_phone


class ActivitySerializer(ModelCleanMixin, serializers.ModelSerializer):
    """Activity: campos explicitos, clean() del modelo, telefono, tipo de
    atencion activo y deteccion de duplicados (mismas reglas que ActivityForm,
    sin scoping por delegacion: decision D4)."""

    class Meta:
        model = Activity
        fields = [
            'id',
            'employee',
            'period',
            'meta',
            'activity_type',
            'service',
            'attention',
            'sub_attention',
            'date',
            'request_description',
            'action_taken',
            'contact_name',
            'contact_phone',
            'status',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'contact_phone': {'validators': [validate_phone]},
        }

    def validate_attention(self, value):
        # Como el formulario: solo items activos, salvo el que la actividad
        # ya tenia asignado al editar.
        unchanged = (
            self.instance is not None
            and self.instance.attention_id == value.pk
        )
        if not value.is_active and not unchanged:
            raise serializers.ValidationError(
                'El tipo de atención seleccionado no está activo.'
            )
        return value

    def validate(self, attrs):
        # 1) Model.clean() (fecha dentro del periodo) via ModelCleanMixin.
        attrs = super().validate(attrs)

        # 2) Duplicados. En PATCH, los campos ausentes salen de la instancia.
        def current(name):
            if name in attrs:
                return attrs[name]
            return getattr(self.instance, name, None)

        employee = current('employee')
        date = current('date')
        activity_type = current('activity_type')
        description = (current('request_description') or '').strip()

        if employee and date and activity_type and description:
            duplicates = Activity.objects.filter(
                employee=employee,
                date=date,
                activity_type=activity_type,
                request_description__iexact=description,
            )
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    'Ya existe una actividad con el mismo funcionario, '
                    'fecha, tipo y solicitud.'
                )
        return attrs