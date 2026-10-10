import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class ModelCleanMixin:
    """Ejecuta Model.clean() dentro del serializer (DRF no lo hace solo)."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        Model = self.Meta.model
        if self.instance is not None:
            obj = copy.copy(self.instance)
            for key, value in attrs.items():
                setattr(obj, key, value)
        else:
            obj = Model(**attrs)
        try:
            obj.clean()
        except DjangoValidationError as e:
            detail = e.message_dict if hasattr(e, "error_dict") else e.messages
            raise serializers.ValidationError(detail)
        return attrs