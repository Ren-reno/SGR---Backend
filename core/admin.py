from datetime import date

from django.contrib import admin, messages
from .models import Delegacion, Cargo, Funcionario, Periodo, Actividad, Evidencia, Validacion


class EvidenciaInline(admin.TabularInline):
    """Inline principal (Plan Fase 5): Evidencia dentro de ActividadAdmin."""
    model = Evidencia
    extra = 0


class ValidacionInline(admin.StackedInline):
    """Inline adicional (Decisión 3 / Plan Fase 5): Validación dentro de
    EvidenciaAdmin. Validacion.evidencia es OneToOneField (relación 1:0..1,
    Decisión 10) -> Django limita este inline a una sola fila como máximo,
    coherente con el diseño sin necesitar max_num explícito."""
    model = Validacion
    extra = 0


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

    # --- Fase 5, lo único que agrega esta fase ---
    inlines = [EvidenciaInline]

    # Fase 6 agrega aquí: get_queryset(), has_change_permission(),
    # has_delete_permission().


@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('codigo', 'actividad', 'fecha', 'estado_revision')
    search_fields = ('codigo', 'actividad__solicitud_problema')
    list_filter = ('estado_revision', 'fecha')
    ordering = ('-fecha',)
    list_select_related = ('actividad',)

    # --- Fase 5, lo único que agrega esta fase ---
    inlines = [ValidacionInline]
    actions = ['aprobar_evidencias_en_lote']
    # Fase 6 agrega aquí: get_queryset(), has_change_permission(),
    # has_delete_permission(), y la restricción de esta acción al grupo
    # Verificador (Decisión 6/9 — explícitamente NO implementada en Fase 5;
    # ver nota bajo el método).

    @admin.action(description='Aprobar evidencias seleccionadas en lote')
    def aprobar_evidencias_en_lote(self, request, queryset):
        """Decisión 9 de decisiones.md, seguida exactamente:

        Crea una Validacion NUEVA (resultado=True, funcionario=verificador
        actual, fecha=hoy) solo para las Evidencias seleccionadas que:
          (a) no tengan ya una Validacion asociada, Y
          (b) tengan archivo cargado.
        Ambos casos que no cumplen se EXCLUYEN del procesamiento y se
        reportan por separado en el mensaje — nunca se hace
        update_or_create sobre una Validacion existente (pisaría un
        resultado previo, ej. un rechazo, sin dejar rastro).

        NOTA — Decisión 9-bis (decisiones.md): además de crear la
        Validacion, esta acción marca Evidencia.estado_revision =
        'Aprobada' en las evidencias efectivamente procesadas. Las
        evidencias EXCLUIDAS (ya validadas o sin archivo) no tocan
        estado_revision bajo ningún motivo.

        NOTA — restricción por grupo Verificador (Decisión 6/9): esta
        acción todavía NO valida en Fase 5 que request.user pertenezca al
        grupo Verificador. Eso es explícitamente Fase 6
        (Plan_Proyecto_SGR_Fusionado.md, sección Fase 6, punto 3). En Fase
        5 la acción es funcional para cualquier staff con permiso de
        cambiar Evidencia; la restricción de grupo se agrega ENCIMA de este
        mismo método en Fase 6, no reemplazándolo.
        """
        # request.user.funcionario puede lanzar RelatedObjectDoesNotExist
        # si un User sin fila Funcionario ejecuta la acción (Decisión 6,
        # caso borde). El seed de Fase 3 cubre a los 3 usuarios de prueba,
        # pero un superuser creado manualmente vía createsuperuser durante
        # debugging no tendría Funcionario propio.
        if not hasattr(request.user, 'funcionario'):
            self.message_user(
                request,
                "Tu usuario no tiene un Funcionario asociado, por lo que "
                "no puede quedar registrado como verificador de la "
                "Validacion. Pide que se cree tu fila de Funcionario "
                "antes de usar esta acción.",
                level=messages.ERROR,
            )
            return

        verificador = request.user.funcionario

        ya_validadas = []
        sin_archivo = []
        procesadas = []

        for evidencia in queryset:
            # hasattr, no evidencia.validacion is None: Validacion.evidencia
            # es OneToOneField -> acceder al atributo inverso sin fila
            # relacionada lanza RelatedObjectDoesNotExist, no devuelve None
            # (mismo patrón de caso borde que Decisión 6, aplicado aquí a
            # Evidencia.validacion en vez de a User.funcionario).
            if hasattr(evidencia, 'validacion'):
                ya_validadas.append(evidencia.codigo)
                continue
            if not evidencia.archivo:
                sin_archivo.append(evidencia.codigo)
                continue

            Validacion.objects.create(
                evidencia=evidencia,
                funcionario=verificador,
                decision='Aprobada',
                fecha=date.today(),
                resultado=True,
            )
            # Decisión 9-bis (ver docstring): solo las procesadas cambian
            # estado_revision. Las excluidas quedan intactas.
            evidencia.estado_revision = 'Aprobada'
            evidencia.save(update_fields=['estado_revision'])
            procesadas.append(evidencia.codigo)

        partes = [f"{len(procesadas)} evidencia(s) aprobada(s)."]
        if ya_validadas:
            partes.append(
                f"{len(ya_validadas)} omitida(s) por ya tener validación: "
                f"{', '.join(ya_validadas)}."
            )
        if sin_archivo:
            partes.append(
                f"{len(sin_archivo)} omitida(s) por no tener archivo "
                f"cargado: {', '.join(sin_archivo)}."
            )

        nivel = messages.SUCCESS if procesadas else messages.WARNING
        self.message_user(request, ' '.join(partes), level=nivel)


@admin.register(Validacion)
class ValidacionAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('id', 'evidencia', 'funcionario', 'decision', 'resultado', 'fecha', 'version')
    search_fields = ('evidencia__codigo', 'funcionario__nombre', 'observacion')
    list_filter = ('decision', 'resultado', 'fecha')
    ordering = ('-fecha',)
    list_select_related = ('evidencia', 'funcionario')
