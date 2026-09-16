from datetime import date

from django.contrib import admin, messages
from .models import Delegacion, Cargo, Funcionario, Periodo, Actividad, Evidencia, Validacion


def _sin_restriccion(request):
    """
    True si request.user es Administrador en cualquiera de sus dos formas
    (superuser técnico de Django, o miembro del grupo "Administrador") y por
    lo tanto no aplica ninguna restricción -- ni de Delegación ni de rol
    (Decisión 6: "Administrador no tiene restricción de ninguna de las dos
    dimensiones").

    Corrección (revisión cruzada): antes de esto, este chequeo doble vivía
    SOLO acá dentro y de forma duplicada -- has_add_permission /
    has_change_permission de ValidacionAdmin y la acción de Fase 5 miraban
    únicamente is_superuser o _es_verificador() por separado, sin el grupo
    Administrador. Con un usuario Administrador que no fuera también
    superuser técnico (posible en producción, aunque no en el seed actual,
    donde admin_sgr es ambas cosas), esos otros dos puntos lo habrían
    bloqueado igual, contradiciendo la Decisión 6. Se centraliza acá y se
    reutiliza en los tres lugares.
    """
    if request.user.is_superuser:
        return True
    return request.user.groups.filter(name="Administrador").exists()


def _delegacion_del_usuario(request):
    """
    Devuelve la Delegacion del Funcionario asociado a request.user, o None si:
    - el usuario no tiene restricción (superuser/Administrador -- ver
      _sin_restriccion), o
    - el usuario no tiene Funcionario asociado (caso borde Decision 6).

    None significa "sin restricción de Delegación" en este contexto, no
    "sin Delegacion asignada" -- se usa exclusivamente para decidir si se
    filtra o no, nunca se compara contra un campo delegacion=None real.
    """
    if _sin_restriccion(request):
        return None
    if not hasattr(request.user, "funcionario"):
        # User sin Funcionario asociado (Decision 6, capa 2) -- no forma
        # parte del seed de Fase 3 ni tiene delegacion propia. Se trata
        # igual que "sin restriccion" a nivel de scoping por Delegacion:
        # no hay contra qué comparar. Las permission-checks de Paso 3/4
        # son las que efectivamente le niegan modificar nada, no este
        # helper.
        return None
    return request.user.funcionario.delegacion


def _es_verificador(request):
    return request.user.groups.filter(name="Verificador").exists()


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

    # --- Fase 6, scoping por Delegación y permisos por objeto ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        delegacion = _delegacion_del_usuario(request)
        if delegacion is None:
            return qs
        return qs.filter(funcionario__delegacion=delegacion)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return True  # obj=None es la vista de lista, no un registro puntual
        delegacion = _delegacion_del_usuario(request)
        if delegacion is None:
            return True
        return obj.funcionario.delegacion_id == delegacion.pk

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if obj is None:
            return True
        delegacion = _delegacion_del_usuario(request)
        if delegacion is None:
            return True
        return obj.funcionario.delegacion_id == delegacion.pk


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

    # --- Fase 6, scoping por Delegación y permisos por objeto ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        delegacion = _delegacion_del_usuario(request)
        if delegacion is None:
            return qs
        return qs.filter(actividad__funcionario__delegacion=delegacion)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return True
        delegacion = _delegacion_del_usuario(request)
        if delegacion is None:
            return True
        return obj.actividad.funcionario.delegacion_id == delegacion.pk

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if obj is None:
            return True
        delegacion = _delegacion_del_usuario(request)
        if delegacion is None:
            return True
        return obj.actividad.funcionario.delegacion_id == delegacion.pk

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
        # --- Fase 6, Paso 4a: restricción de rol ---
        # Bypass de Administrador/superuser vía _sin_restriccion(): sin esto,
        # admin_sgr (que el seed no agrega al grupo Verificador) quedaría
        # bloqueado para ejecutar esta acción, contradiciendo la Decisión 6.
        if not (_es_verificador(request) or _sin_restriccion(request)):
            self.message_user(
                request,
                "Solo el grupo Verificador puede ejecutar esta acción.",
                level=messages.ERROR,
            )
            return

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

    # --- Fase 6, scoping por Delegación y restricción de rol Verificador ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        delegacion = _delegacion_del_usuario(request)
        if delegacion is None:
            return qs
        return qs.filter(evidencia__actividad__funcionario__delegacion=delegacion)

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        return _es_verificador(request) or _sin_restriccion(request)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if not (_es_verificador(request) or _sin_restriccion(request)):
            return False
        if obj is None:
            return True
        delegacion = _delegacion_del_usuario(request)
        if delegacion is None:
            return True
        return obj.evidencia.actividad.funcionario.delegacion_id == delegacion.pk

    def has_delete_permission(self, request, obj=None):
        # Decisión de diseño (Decisión 12, decisiones.md): no se permite
        # borrar Validacion desde el Admin, ni siquiera a Administrador.
        # Coherente con la política PROTECT / conservar historial de la
        # Decisión 8 y con la razón de ser de la Decisión 9 (nunca perder
        # el rastro de una revisión ya emitida: por eso la acción de
        # Fase 5 usa create() y nunca update_or_create).
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Sin esto, el desplegable de "Evidencia" en
        # /admin/core/validacion/add/ mostraba TODAS las Evidencias de
        # ambas Delegaciones, y has_add_permission no alcanza a impedir que
        # un Verificador cree una Validacion sobre una Evidencia ajena a su
        # Delegación (has_add_permission solo valida rol, no delegación,
        # porque en el alta todavía no existe un `obj` contra qué
        # comparar). Se filtra acá, que es el único lugar del que se
        # dispone de la Evidencia concreta antes de guardar.
        if db_field.name == "evidencia":
            delegacion = _delegacion_del_usuario(request)
            if delegacion is not None:
                kwargs["queryset"] = Evidencia.objects.filter(
                    actividad__funcionario__delegacion=delegacion
                )
        # Corrección (Fase 6, Paso 4c): mismo problema que "evidencia" de
        # arriba, pero para "funcionario" -- sin esto, cualquier Verificador
        # podía asignar la Validacion a un Funcionario ajeno a su Delegación
        # (o que ni siquiera pertenece al grupo Verificador), porque
        # has_add_permission solo valida rol y formfield_for_foreignkey no
        # tocaba este campo. Se filtra a Funcionarios que pertenecen al
        # grupo Verificador y, si el usuario tiene Delegación propia, a los
        # de esa misma Delegación.
        if db_field.name == "funcionario":
            kwargs["queryset"] = Funcionario.objects.filter(
                user__groups__name="Verificador"
            ).distinct()
            delegacion = _delegacion_del_usuario(request)
            if delegacion is not None:
                kwargs["queryset"] = kwargs["queryset"].filter(
                    delegacion=delegacion
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
