from django.core.exceptions import ValidationError
from django.db import models

from organization.models import Employee


class Period(models.Model):
    """Antes Periodo (Decisión 13). inicio -> start_date, termino ->
    end_date, dias_computables -> computable_days, estado -> status
    (CharField de texto libre, no booleano -- por eso status y no
    is_active; sigue pendiente decidir si pasa a choices, ver decisiones.md
    / Pendientes), umbral_ambar -> amber_threshold, umbral_colectivo ->
    collective_threshold, version_parametros -> parameters_version."""
    start_date = models.DateField()
    end_date = models.DateField()
    computable_days = models.PositiveIntegerField()
    status = models.CharField(max_length=30)
    amber_threshold = models.DecimalField(max_digits=5, decimal_places=2)
    collective_threshold = models.DecimalField(max_digits=5, decimal_places=2)
    parameters_version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Período {self.start_date} – {self.end_date}"


class CatalogItem(models.Model):
    """Antes ElementoCatalogo (Decisión 13: convención en inglés). Entidad
    genérica ya prevista en el diseño de dominio de Actividad 3 para
    modelar los catálogos abiertos/administrables de clasificación de
    Activity, a diferencia de los de conjunto cerrado (que se modelan
    con TextChoices -- ver Compromiso.estado).

    Decisión de alcance (Fase 2, paso 2.1, plan Eva 2 formativa): de los 4
    campos de texto libre de Activity (activity_type, service, attention,
    sub_attention), solo `attention` se conecta a esta entidad en esta
    entrega. Los otros 3 quedan como CharField sin cambios, pendientes
    para Eva 3. Motivo, no arbitrario: es el cambio más invasivo del lote
    porque toca datos ya cargados por el seed (Decisión 4), así que se
    conecta solo uno como demostración de relación real, dejando el resto
    pendiente -- tal como recomienda el plan de trabajo.

    `attention` es el candidato elegido, no uno cualquiera de los 4:
    la Decisión 4 ya deja verificado contra la fuente (`ppt-original.md`,
    Diapositiva 8) que "Tipo Atención" y "Sub Atención" son los únicos 2
    de los 4 campos con un catálogo cerrado real en la documentación del
    caso -- `service` y `activity_type` son de libre definición del
    equipo, sin catálogo que verificar. Entre esos 2 candidatos con
    catálogo real, se elige `attention` (no `sub_attention`) por ser el
    campo padre de la relación Atención/Subatención que ya describe esa
    misma Diapositiva 8 -- migrar el padre primero dejando el hijo como
    texto libre es la migración parcial más simple de completar después,
    sin que quede una jerarquía a medio migrar en el sentido inverso.

    `category` distingue el catálogo de `attention` de cualquier otro
    catálogo que se agregue después (`sub_attention`, `service`,
    `activity_type` en Eva 3) dentro de la misma tabla genérica, en vez de
    crear una tabla nueva por cada campo migrado -- consistente con que
    esta es una entidad "genérica" según el propio diseño de dominio.

    Nota de secuenciación (no un olvido): este modelo todavía no tiene
    ModelAdmin propio en este patch. El registro en Django Admin de
    CatalogItem, Meta y Compromiso es paso 2.5 del plan (rama propia,
    posterior a que existan los 3 modelos), para que las tres entidades
    queden documentadas y revisadas juntas con el mismo patrón que ya usan
    organization/admin.py y el resto de performance/admin.py. Mientras
    tanto, ActivityAdmin.formfield_for_foreignkey no necesita tocarse: el
    desplegable de `attention` ya filtra correctamente por
    limit_choices_to (categoría 'attention') sin depender de que
    CatalogItem tenga su propio Admin -- solo no hay forma de *crear* un
    CatalogItem nuevo desde el Admin hasta que se mergee el paso 2.5.
    """
    CATEGORY_ATTENTION = 'attention'
    CATEGORY_CHOICES = [
        (CATEGORY_ATTENTION, 'Tipo Atención'),
    ]

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'name'], name='unique_catalog_item_per_category'
            )
        ]
        ordering = ('category', 'name')

    def __str__(self):
        return self.name


class Activity(models.Model):
    """Antes Actividad (Decisión 13). funcionario -> employee, periodo ->
    period, tipo_actividad -> activity_type, servicio -> service,
    atencion -> attention, subatencion -> sub_attention, fecha -> date,
    solicitud_problema -> request_description, accion -> action_taken,
    contacto -> contact_name, telefono -> contact_phone,
    estado -> status.

    Fase 2 (paso 2.1): `attention` deja de ser CharField de texto libre y
    pasa a FK hacia CatalogItem (PROTECT, coherente con la Decisión 8 --
    igual política que employee/period). `activity_type`, `service` y
    `sub_attention` NO cambian en este patch -- ver docstring de
    CatalogItem para la justificación de por qué solo este campo migra
    ahora."""
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='activities'
    )
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT, related_name='activities'
    )
    activity_type = models.CharField(max_length=100)
    service = models.CharField(max_length=100)
    attention = models.ForeignKey(
        CatalogItem,
        on_delete=models.PROTECT,
        related_name='activities',
        limit_choices_to={'category': CatalogItem.CATEGORY_ATTENTION},
    )
    sub_attention = models.CharField(max_length=100)
    date = models.DateField()
    request_description = models.TextField()
    action_taken = models.TextField()
    contact_name = models.CharField(max_length=150, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=30)

    def clean(self):
        super().clean()
        if self.period_id is None or self.date is None:
            return
        if not (self.period.start_date <= self.date <= self.period.end_date):
            raise ValidationError({
                'date': (
                    f"La fecha ({self.date}) debe estar dentro del "
                    f"período asignado ({self.period.start_date} – "
                    f"{self.period.end_date})."
                )
            })

    def __str__(self):
        return f"Actividad {self.pk} — {self.activity_type}"


class Evidence(models.Model):
    """Antes Evidencia (Decisión 13). codigo -> code, actividad -> activity,
    archivo -> file, fecha -> date, metadatos -> metadata,
    estado_revision -> review_status."""
    code = models.CharField(max_length=30, primary_key=True)
    activity = models.ForeignKey(
        Activity, on_delete=models.PROTECT, related_name='evidence_items'
    )
    file = models.FileField(upload_to='evidence/%Y/%m/')
    date = models.DateField()
    metadata = models.TextField(blank=True)
    review_status = models.CharField(max_length=30, default='pendiente')

    def __str__(self):
        return self.code


class Validation(models.Model):
    """Antes Validacion (Decisión 13). evidencia -> evidence, funcionario ->
    employee, observacion -> notes, resultado -> result. decision y
    version ya estaban en inglés."""
    evidence = models.OneToOneField(
        Evidence, on_delete=models.CASCADE, related_name='validation'
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='validations_performed'
    )
    decision = models.CharField(max_length=30)
    date = models.DateField()
    notes = models.TextField(blank=True)
    result = models.BooleanField()
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Validación {self.pk} — {self.evidence_id}"
