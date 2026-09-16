from django.contrib import admin
from .models import Delegacion, Cargo, Funcionario, Periodo, Actividad, Evidencia, Validacion


@admin.register(Delegacion)
class DelegacionAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('id', 'nombre', 'ambito', 'estado')
    search_fields = ('id', 'nombre')
    list_filter = ('ambito', 'estado')
    ordering = ('nombre',)


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('nombre', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado',)
    ordering = ('nombre',)


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('id_institucional', 'nombre', 'delegacion', 'cargo', 'user', 'estado')
    search_fields = ('id_institucional', 'nombre', 'user__username')
    list_filter = ('delegacion', 'cargo', 'estado')
    ordering = ('nombre',)
    list_select_related = ('delegacion', 'cargo', 'user')


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('inicio', 'termino', 'estado', 'dias_computables', 'version_parametros')
    search_fields = ('estado',)
    list_filter = ('estado',)
    ordering = ('-inicio',)


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = (
        'id', 'fecha', 'funcionario', 'periodo', 'tipo_actividad',
        'atencion', 'subatencion', 'servicio', 'estado',
    )
    search_fields = (
        'solicitud_problema', 'accion', 'contacto',
        'funcionario__nombre', 'funcionario__id_institucional',
    )
    list_filter = ('funcionario__delegacion', 'estado', 'periodo')
    ordering = ('-fecha',)
    list_select_related = ('funcionario', 'funcionario__delegacion', 'periodo')


@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('codigo', 'actividad', 'fecha', 'estado_revision')
    search_fields = ('codigo', 'actividad__solicitud_problema')
    list_filter = ('estado_revision', 'fecha')
    ordering = ('-fecha',)
    list_select_related = ('actividad',)


@admin.register(Validacion)
class ValidacionAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('id', 'evidencia', 'funcionario', 'decision', 'resultado', 'fecha', 'version')
    search_fields = ('evidencia__codigo', 'funcionario__nombre', 'observacion')
    list_filter = ('decision', 'resultado', 'fecha')
    ordering = ('-fecha',)
    list_select_related = ('evidencia', 'funcionario')
