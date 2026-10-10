from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError
from django.test import SimpleTestCase
from rest_framework import serializers

from api.exceptions import api_exception_handler
from api.mixins import ModelCleanMixin
from api.pagination import StandardPagination
from api.validators import validate_phone


class FakeModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def clean(self):
        if self.__dict__.get("bad"):
            raise DjangoValidationError("regla del modelo violada")


class FakeSerializer(ModelCleanMixin, serializers.Serializer):
    bad = serializers.BooleanField(required=False)

    class Meta:
        model = FakeModel


class ValidatePhoneTests(SimpleTestCase):
    def test_vacio_es_valido(self):
        self.assertEqual(validate_phone(""), "")

    def test_letras_rechazadas(self):
        with self.assertRaises(serializers.ValidationError):
            validate_phone("abc")

    def test_pocos_digitos_rechazado(self):
        with self.assertRaises(serializers.ValidationError):
            validate_phone("123")

    def test_telefono_valido(self):
        self.assertEqual(validate_phone("+56 9 1234 5678"), "+56 9 1234 5678")


class ExceptionHandlerTests(SimpleTestCase):
    def test_protected_error_devuelve_409(self):
        exc = ProtectedError("protegido", set())
        response = api_exception_handler(exc, {})
        self.assertEqual(response.status_code, 409)


class PaginationTests(SimpleTestCase):
    def test_tamano_por_defecto_25(self):
        self.assertEqual(StandardPagination.page_size, 25)
        self.assertEqual(StandardPagination.max_page_size, 100)


class ModelCleanMixinTests(SimpleTestCase):
    def test_clean_ok_en_creacion(self):
        s = FakeSerializer(data={"bad": False})
        self.assertTrue(s.is_valid(), s.errors)

    def test_clean_falla_en_creacion(self):
        s = FakeSerializer(data={"bad": True})
        self.assertFalse(s.is_valid())
        self.assertIn("regla del modelo violada", str(s.errors))

    def test_clean_falla_en_actualizacion_parcial(self):
        s = FakeSerializer(FakeModel(bad=False), data={"bad": True}, partial=True)
        self.assertFalse(s.is_valid())