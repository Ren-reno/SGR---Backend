from django.utils import timezone
from rest_framework import serializers

from performance.models import Activity, Commitment

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


class CommitmentSerializer(ModelCleanMixin, serializers.ModelSerializer):
    """Commitment: campos explicitos, clean() del modelo (la delegacion debe
    ser la del responsable), fecha comprometida no anterior a hoy y deteccion
    de duplicados (mismas reglas que CommitmentForm, sin scoping por
    delegacion: decision D4)."""

    class Meta:
        model = Commitment
        fields = [
            'id',
            'delegation',
            'responsible',
            'origin',
            'requester',
            'territory',
            'due_date',
            'support_area',
            'status',
            'observation',
        ]
        read_only_fields = ['id']

    def validate_due_date(self, value):
        # Como CommitmentForm.clean_due_date: solo se exige al crear o cuando
        # la fecha cambia, para que un compromiso vencido siga siendo editable
        # (por ejemplo pasarlo a "realizado") sin tocar su fecha.
        creating = self.instance is None
        changed = self.instance is not None and self.instance.due_date != value
        if (creating or changed) and value < timezone.localdate():
            raise serializers.ValidationError(
                'La fecha comprometida no puede ser anterior a hoy.'
            )
        return value

    def validate(self, attrs):
        # 1) Model.clean() (delegacion = delegacion del responsable).
        attrs = super().validate(attrs)

        # 2) Duplicados. En PATCH, los campos ausentes salen de la instancia.
        def current(name):
            if name in attrs:
                return attrs[name]
            return getattr(self.instance, name, None)

        responsible = current('responsible')
        due_date = current('due_date')
        origin = current('origin')
        requester = current('requester')
        territory = current('territory')

        if responsible and due_date and origin and requester and territory:
            duplicates = Commitment.objects.filter(
                responsible=responsible,
                due_date=due_date,
                origin__iexact=origin,
                requester__iexact=requester,
                territory__iexact=territory,
            )
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    'Ya existe un compromiso con el mismo responsable, '
                    'fecha, origen, solicitante y territorio.'
                )
        return attrs
