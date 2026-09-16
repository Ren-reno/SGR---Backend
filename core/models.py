from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User


class Delegacion(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=150)
    ambito = models.CharField(max_length=100)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Cargo(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Funcionario(models.Model):
    id_institucional = models.CharField(max_length=20, primary_key=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='funcionario'
    )
    delegacion = models.ForeignKey(
        Delegacion, on_delete=models.PROTECT, related_name='funcionarios'
    )
    cargo = models.ForeignKey(
        Cargo, on_delete=models.PROTECT, related_name='funcionarios'
    )
    nombre = models.CharField(max_length=150)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Periodo(models.Model):
    inicio = models.DateField()
    termino = models.DateField()
    dias_computables = models.PositiveIntegerField()
    estado = models.CharField(max_length=30)
    umbral_ambar = models.DecimalField(max_digits=5, decimal_places=2)
    umbral_colectivo = models.DecimalField(max_digits=5, decimal_places=2)
    version_parametros = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Período {self.inicio} – {self.termino}"


class Actividad(models.Model):
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.PROTECT, related_name='actividades'
    )
    periodo = models.ForeignKey(
        Periodo, on_delete=models.PROTECT, related_name='actividades'
    )
    tipo_actividad = models.CharField(max_length=100)
    servicio = models.CharField(max_length=100)
    atencion = models.CharField(max_length=100)
    subatencion = models.CharField(max_length=100)
    fecha = models.DateField()
    solicitud_problema = models.TextField()
    accion = models.TextField()
    contacto = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    estado = models.CharField(max_length=30)

    def clean(self):
        # Fase 5 — Decisión 1 / Plan Fase 5: la fecha de la Actividad debe
        # caer dentro del rango [periodo.inicio, periodo.termino] del
        # Periodo asignado. Sin periodo_id todavía (ej. formulario a medio
        # llenar en el Admin) no hay nada contra qué validar: se omite en
        # silencio y deja que la validación NOT NULL de Django se encargue
        # de exigir el campo por su cuenta.
        super().clean()
        if self.periodo_id is None or self.fecha is None:
            return
        if not (self.periodo.inicio <= self.fecha <= self.periodo.termino):
            raise ValidationError({
                'fecha': (
                    f"La fecha ({self.fecha}) debe estar dentro del "
                    f"período asignado ({self.periodo.inicio} – "
                    f"{self.periodo.termino})."
                )
            })

    def __str__(self):
        return f"Actividad {self.pk} — {self.tipo_actividad}"


class Evidencia(models.Model):
    codigo = models.CharField(max_length=30, primary_key=True)
    actividad = models.ForeignKey(
        Actividad, on_delete=models.PROTECT, related_name='evidencias'
    )
    archivo = models.FileField(upload_to='evidencias/%Y/%m/')
    fecha = models.DateField()
    metadatos = models.TextField(blank=True)
    estado_revision = models.CharField(max_length=30, default='pendiente')

    def __str__(self):
        return self.codigo


class Validacion(models.Model):
    evidencia = models.OneToOneField(
        Evidencia, on_delete=models.CASCADE, related_name='validacion'
    )
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.PROTECT, related_name='validaciones_realizadas'
    )
    decision = models.CharField(max_length=30)
    fecha = models.DateField()
    observacion = models.TextField(blank=True)
    resultado = models.BooleanField()
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Validación {self.pk} — {self.evidencia_id}"