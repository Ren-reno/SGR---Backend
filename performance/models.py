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


class Activity(models.Model):
    """Antes Actividad (Decisión 13). funcionario -> employee, periodo ->
    period, tipo_actividad -> activity_type, servicio -> service,
    atencion -> attention, subatencion -> sub_attention, fecha -> date,
    solicitud_problema -> request_description, accion -> action_taken,
    contacto -> contact_name, telefono -> contact_phone,
    estado -> status."""
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='activities'
    )
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT, related_name='activities'
    )
    activity_type = models.CharField(max_length=100)
    service = models.CharField(max_length=100)
    attention = models.CharField(max_length=100)
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
