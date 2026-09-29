"""Borrado lógico (Fase 3, Decisión 20).

Patrón: en vez de borrar la fila, se marca `deleted_at` con la fecha del
borrado. La fila sigue en la base de datos (se conserva el rastro que exige
la Guía: RF-036, CA-09), pero desaparece de las consultas normales.

Cómo se usa:

    class Algo(SoftDeleteModel):
        ...

    Algo.objects        -> solo registros vivos (lo que usan listados,
                           desplegables, formularios y el Admin)
    Algo.all_objects    -> vivos y eliminados (para mantenimiento y tests)
    obj.soft_delete()   -> esconde el registro
    obj.restore()       -> lo vuelve a mostrar
    obj.delete()        -> hace soft_delete(), NUNCA borra la fila
    qs.delete()         -> igual: borrado lógico de cada fila
    obj.hard_delete()   -> único camino al borrado físico; es explícito y no
                           lo usa ningún flujo normal del proyecto

Por qué `objects` es el filtrado y va primero: Django usa el primer manager
declarado como `_default_manager`, y de ahí salen los listados del Admin, los
desplegables de los ModelForm y los managers de relaciones inversas
(`activity.evidence_items`). Así todos ocultan lo eliminado sin tocar cada
vista. Las FK hacia adelante (`evidence.activity`) usan el `_base_manager`
(sin filtro), por eso un registro antiguo que apunta a algo eliminado sigue
pudiendo leerlo sin errores.
"""
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Borrado lógico de cada fila (no un DELETE de SQL).

        Se recorre fila por fila, y no con un solo update(), para que cada
        modelo aplique sus reglas (`_before_soft_delete`). Es todo o nada:
        si una fila no se puede eliminar, no se elimina ninguna.
        """
        count = 0
        with transaction.atomic():
            for obj in self:
                if obj.soft_delete():
                    count += 1
        if not count:
            return 0, {}
        return count, {self.model._meta.label: count}

    def hard_delete(self):
        """Borrado físico real. Solo para mantenimiento; ver el docstring."""
        return super().delete()

    def dead(self):
        """Solo los eliminados. Se usa sobre `all_objects`."""
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(
        null=True, blank=True, editable=False,
        help_text="Si tiene fecha, el registro está eliminado (borrado lógico).",
    )

    # El orden importa: el primero es el `_default_manager`.
    objects = SoftDeleteManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()

    class Meta:
        abstract = True

    def _before_soft_delete(self):
        """Gancho para reglas propias de cada modelo.

        Se ejecuta dentro de la transacción del borrado. Puede lanzar
        ProtectedError para impedirlo, o eliminar lógicamente a sus hijos.
        """

    def soft_delete(self):
        """Esconde el registro. Devuelve True si lo eliminó ahora, False si
        ya estaba eliminado."""
        if self.deleted_at is not None:
            return False
        with transaction.atomic():
            self._before_soft_delete()
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])
        return True

    def restore(self):
        """Vuelve a mostrar el registro. No reevalúa sus relaciones: no
        restaura a los hijos que se eliminaron junto con él."""
        if self.deleted_at is None:
            return False
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
        return True

    def delete(self, using=None, keep_parents=False):
        # Misma forma de retorno que Model.delete(): (total, {modelo: n}).
        if self.soft_delete():
            return 1, {self._meta.label: 1}
        return 0, {}

    def hard_delete(self, using=None, keep_parents=False):
        """Borrado físico real. Solo para mantenimiento; ver el docstring."""
        return super().delete(using=using, keep_parents=keep_parents)

    def validate_unique(self, exclude=None):
        """Los valores únicos (PK natural, OneToOne) siguen ocupados por las
        filas eliminadas, pero Django comprueba la unicidad con el manager
        filtrado, así que no las vería y el error saldría recién al guardar
        como un IntegrityError (pantalla 500). Se comprueba también contra
        las eliminadas para devolver un error de formulario normal."""
        super().validate_unique(exclude=exclude)
        errors = {}
        for field in self._meta.concrete_fields:
            if not field.unique or (exclude and field.name in exclude):
                continue
            value = getattr(self, field.attname)
            if value is None:
                continue
            clash = type(self).all_objects.dead().filter(**{field.attname: value})
            if not self._state.adding:
                clash = clash.exclude(pk=self.pk)
            if clash.exists():
                errors[field.name] = ValidationError(
                    "Ya existe un registro eliminado con este valor; "
                    "no se puede crear otro igual.",
                    code='unique_deleted',
                )
        if errors:
            raise ValidationError(errors)
