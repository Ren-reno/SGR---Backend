from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from organization.models import Employee, Position


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


class Meta(models.Model):
    """Entidad nueva (Fase 2, paso 2.2 -- Decisión 14 ya confirma que
    existe, sin haberse implementado todavía a la fecha de esa
    anotación).

    Nota de nomenclatura (no una decisión de este patch, solo una
    advertencia): "Meta" es también el nombre que usa Django para la
    clase interna de configuración de cada modelo (`class Meta:` con
    ordering, verbose_name, etc.). No hay colisión real -- Django siempre
    resuelve por nombre completo (`performance.Meta` como modelo,
    `Activity.Meta` como clase interna de otro modelo), confirmado con
    `manage.py check` y `makemigrations` sin advertencias -- pero conviene
    tenerlo presente al leer el código de acá en adelante: un `self.Meta`
    dentro de OTRO modelo de este archivo se refiere a la configuración de
    ESE modelo, nunca a esta entidad. Se mantiene el nombre `Meta` porque
    así está fijado en el glosario del proyecto (Guía para Estudiantes,
    sección 8), en la Decisión 14 y en el propio plan de trabajo de esta
    entrega -- cambiarlo sería una decisión de nomenclatura nueva, no
    pedida.

    Campos según el glosario del proyecto (Guía para Estudiantes, sección
    8: "Meta | Ítem, funcionario/cargo, valor objetivo, unidad y
    ponderador."):

    - item_name: el "Ítem" del glosario. CharField de texto libre, mismo
      patrón que Activity.activity_type/service (Decisión 4) -- no FK a
      CatalogItem. La propia Decisión 14 descarta explícitamente
      vincular Meta a un elemento de catálogo como una de las tres
      alternativas simuladas ("FK inversa desde Meta hacia un elemento de
      catálogo"), precisamente porque esa opción sobrecuenta el avance
      (RN-009).
    - position: el "cargo" de "funcionario/cargo" en el glosario. Se
      eligió Position (Cargo) y no Employee (Funcionario) porque RN-001
      es explícita: "la suma de ponderadores aplicables a un CARGO y
      período deberá ser 100%" -- la regla agrupa por cargo, no por
      funcionario individual.
    - period: FK a Period, mismo on_delete=PROTECT que ya usa
      Activity.period (Decisión 8).
    - target_value: el "valor objetivo". RN-002: "la meta de un ítem
      cuantitativo deberá ser mayor que cero" -- validado en clean().
    - unit: la "unidad" del glosario (texto libre: p. ej. "actividades",
      "%", "informes").
    - weight: el "ponderador", como porcentaje (0-100). Sujeto a RN-001.

    on_delete=PROTECT en ambas FK, coherente con la política ya fijada en
    la Decisión 8 para el resto del modelo (period, employee en Activity;
    delegation, position en Employee)."""
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name='goals'
    )
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT, related_name='goals'
    )
    item_name = models.CharField(max_length=150)
    target_value = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    weight = models.DecimalField(max_digits=5, decimal_places=2)

    def clean(self):
        super().clean()
        errors = {}

        # RN-002: "la meta de un ítem cuantitativo deberá ser mayor que
        # cero". No hay campo separado para distinguir un ítem cuantitativo
        # de uno porcentual en el alcance actual (RN-002 también menciona
        # ítems porcentuales con fórmula propia, fuera de este paso), así
        # que se aplica la validación mínima común a target_value.
        if self.target_value is not None and self.target_value <= 0:
            errors['target_value'] = (
                f"El valor objetivo ({self.target_value}) debe ser mayor "
                "que cero (RN-002)."
            )

        # RN-001: "la suma de ponderadores aplicables a un cargo y período
        # deberá ser 100%, salvo excepción formalmente configurada". El
        # mecanismo de excepción formal no está definido todavía en
        # ningún documento del proyecto (ver docs/decisiones.md) y no es
        # parte del alcance de este paso -- queda pendiente para cuando
        # se confirme. Lo que sí se valida acá, sin esperar esa
        # definición, es que la suma NUNCA exceda 100%: eso es un error
        # de carga en cualquier escenario, con o sin excepción formal,
        # y es detectable ya con los datos de esta entidad.
        #
        # No se exige aquí que la suma sea EXACTAMENTE 100% en cada alta
        # individual -- un cargo puede ir cargando sus metas una por una
        # y sumar menos de 100% mientras el conjunto está incompleto; RN-001
        # describe una propiedad del conjunto completo, no una condición
        # que cada alta parcial deba cumplir por sí sola.
        if self.position_id is not None and self.period_id is not None and self.weight is not None:
            other_weights = Meta.objects.filter(
                position_id=self.position_id, period_id=self.period_id
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('weight')
            )['total'] or Decimal('0')
            total_with_self = other_weights + self.weight
            if total_with_self > Decimal('100'):
                errors['weight'] = (
                    f"La suma de ponderadores para este cargo y período "
                    f"sería {total_with_self}%, superando el 100% "
                    f"permitido (RN-001). Ponderador ya asignado a otras "
                    f"metas del mismo cargo/período: {other_weights}%."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Meta {self.item_name} — {self.position} ({self.period})"


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
    ahora.

    Fase 2 (paso 2.3): `meta` es FK a Meta, on_delete=PROTECT. Regla de
    negocio ya confirmada por el docente en la Decisión 14 (no una
    decisión nueva de este patch): una actividad aporta a una sola meta,
    no a varias, y NO se infiere por coincidencia con los 4 campos de
    clasificación (activity_type, service, attention, sub_attention) --
    esa alternativa fue evaluada y descartada explícitamente porque una
    actividad podía coincidir con más de un clasificador y sumar de más a
    varias metas a la vez. Nullable porque una Activity puede registrarse
    sin imputar a ninguna meta todavía -- las 2 Activity que ya carga
    seed_sgr.py no se modifican en este patch y simplemente quedan con
    meta=NULL, sin ningún tratamiento especial adicional."""
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='activities'
    )
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT, related_name='activities'
    )
    meta = models.ForeignKey(
        Meta, on_delete=models.PROTECT, related_name='activities',
        null=True, blank=True,
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
