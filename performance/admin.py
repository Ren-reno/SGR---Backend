from datetime import date

from django.contrib import admin, messages

from organization.models import Employee
from .models import Period, Activity, Evidence, Validation


def _unrestricted(request):
    """
    True si request.user es Administrador en cualquiera de sus dos formas
    (superuser técnico de Django, o miembro del grupo "Administrador") y por
    lo tanto no aplica ninguna restricción -- ni de Delegación ni de rol
    (Decisión 6: "Administrador no tiene restricción de ninguna de las dos
    dimensiones").

    Antes _sin_restriccion (Decisión 13: renombrado a inglés).

    Corrección (revisión cruzada): antes de esto, este chequeo doble vivía
    SOLO acá dentro y de forma duplicada -- has_add_permission /
    has_change_permission de ValidationAdmin y la acción de Fase 5 miraban
    únicamente is_superuser o _is_verifier() por separado, sin el grupo
    Administrador. Con un usuario Administrador que no fuera también
    superuser técnico (posible en producción, aunque no en el seed actual,
    donde admin_sgr es ambas cosas), esos otros dos puntos lo habrían
    bloqueado igual, contradiciendo la Decisión 6. Se centraliza acá y se
    reutiliza en los tres lugares.
    """
    if request.user.is_superuser:
        return True
    return request.user.groups.filter(name="Administrador").exists()


class _NoEmployee:
    """
    Sentinel devuelto por _user_delegation() para el caso "usuario sin
    Employee asociado y sin _unrestricted()" (Decision 6, caso borde,
    capa 2).

    Antes _SinFuncionario (Decisión 13: renombrado a inglés).

    Corrección de seguridad (Bug 2, revisión posterior a la primera entrega
    de Fase 6): antes de esto, este caso devolvía None, el mismo valor que
    "sin restricción" (superuser/Administrador). get_queryset() y los
    has_change_permission/has_delete_permission de los tres ModelAdmin
    interpretaban ambos None de la misma forma con `if delegation is None:
    return qs` / `return True`, así que un User sin Employee -- ej. un
    createsuperuser manual sin is_superuser=True, o cualquier cuenta de
    staff creada fuera del seed -- terminaba viendo y pudiendo modificar
    TODOS los registros de TODAS las Delegaciones, exactamente lo opuesto
    de lo que exige la Decisión 6 ("scoping por Delegación" es la regla; la
    única excepción explícita es Administrador vía _unrestricted()).

    Se usa una clase sentinel en vez de, por ejemplo, un string mágico o un
    objeto Delegation "vacío", porque necesita ser un valor que:
    - sea trivialmente distinguible de None (para no romper la rama de
      "sin restricción" real) y de cualquier instancia real de Delegation
      (para que `== delegation.pk` de las comparaciones existentes falle
      limpio en vez de coincidir por accidente), y
    - no requiera cambiar la firma pública de _user_delegation() ni
      el tipo de dato que ya devuelve en el resto de los casos (sigue
      devolviendo None o una Delegation real; esto es un tercer valor
      posible del mismo return, no un cambio de contrato).
    """
    pass


_NO_EMPLOYEE = _NoEmployee()


def _user_delegation(request):
    """
    Antes _delegacion_del_usuario (Decisión 13: renombrado a inglés).

    Devuelve:
    - None si el usuario no tiene restricción (superuser/Administrador --
      ver _unrestricted): "sin restricción de Delegación", se usa
      exclusivamente para decidir si se filtra o no, nunca se compara
      contra un campo delegation=None real.
    - _NO_EMPLOYEE si el usuario no tiene Employee asociado (caso
      borde Decision 6) y tampoco es Administrador/superuser: a
      diferencia de None, este valor NO habilita bypass de scoping --
      ver _NoEmployee arriba (Bug 2). Quien llama debe negar acceso
      (qs.none() / False) en vez de tratarlo como ausencia de Delegación.
    - la Delegation real del Employee en cualquier otro caso.
    """
    if _unrestricted(request):
        return None
    if not hasattr(request.user, "employee"):
        return _NO_EMPLOYEE
    return request.user.employee.delegation


def _is_verifier(request):
    """Antes _es_verificador (Decisión 13: renombrado a inglés)."""
    return request.user.groups.filter(name="Verificador").exists()


class EvidenceInline(admin.TabularInline):
    """Inline principal (Plan Fase 5): Evidence dentro de ActivityAdmin.
    Antes EvidenciaInline (Decisión 13)."""
    model = Evidence
    extra = 0


class ValidationInline(admin.StackedInline):
    """Inline adicional (Decisión 3 / Plan Fase 5): Validation dentro de
    EvidenceAdmin. Validation.evidence es OneToOneField (relación 1:0..1,
    Decisión 10) -> Django limita este inline a una sola fila como máximo,
    coherente con el diseño sin necesitar max_num explícito.
    Antes ValidacionInline (Decisión 13)."""
    model = Validation
    extra = 0


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('start_date', 'end_date', 'status', 'computable_days', 'parameters_version')
    search_fields = ('status',)
    list_filter = ('status',)
    ordering = ('-start_date',)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    #
    # Fase 2 (paso 2.3): `meta` se agrega a list_display y
    # list_select_related -- mismo criterio que period/employee: mostrar
    # la relación en el listado y evitar N+1 al resolver su __str__.
    list_display = (
        'id', 'date', 'employee', 'period', 'meta', 'activity_type',
        'attention', 'sub_attention', 'service', 'status',
    )
    search_fields = (
        'request_description', 'action_taken', 'contact_name',
        'employee__name', 'employee__institutional_id',
    )
    list_filter = ('employee__delegation', 'status', 'period')
    ordering = ('-date',)
    list_select_related = ('employee', 'employee__delegation', 'period', 'meta', 'attention')

    # --- Fase 5, lo único que agrega esta fase ---
    inlines = [EvidenceInline]

    # --- Fase 6, scoping por Delegación y permisos por objeto ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        delegation = _user_delegation(request)
        if delegation is None:
            return qs
        if delegation is _NO_EMPLOYEE:
            # Bug 2: un User sin Employee asociado y sin
            # _unrestricted() no tiene Delegación contra la cual
            # comparar -- la Decisión 6 dice "scoping por Delegación" como
            # regla general, y el único exento es Administrador, no este
            # caso. Sin fila Employee no hay Delegación de la que
            # "vea todo lo de su Delegación": el resultado correcto es
            # ningún registro, no todos.
            return qs.none()
        return qs.filter(employee__delegation=delegation)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return True  # obj=None es la vista de lista, no un registro puntual
        delegation = _user_delegation(request)
        if delegation is None:
            return True
        if delegation is _NO_EMPLOYEE:
            return False  # Bug 2: sin Delegación contra qué comparar -> denegar
        return obj.employee.delegation_id == delegation.pk

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if obj is None:
            return True
        delegation = _user_delegation(request)
        if delegation is None:
            return True
        if delegation is _NO_EMPLOYEE:
            return False  # Bug 2: mismo criterio que has_change_permission arriba
        return obj.employee.delegation_id == delegation.pk


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('code', 'activity', 'date', 'review_status')
    search_fields = ('code', 'activity__request_description')
    list_filter = ('review_status', 'date')
    ordering = ('-date',)
    list_select_related = ('activity',)

    # --- Fase 5, lo único que agrega esta fase ---
    inlines = [ValidationInline]
    actions = ['approve_evidence_in_bulk']

    # --- Fase 6, scoping por Delegación y permisos por objeto ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        delegation = _user_delegation(request)
        if delegation is None:
            return qs
        if delegation is _NO_EMPLOYEE:
            # Bug 2: ver comentario equivalente en ActivityAdmin.get_queryset.
            return qs.none()
        return qs.filter(activity__employee__delegation=delegation)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return True
        delegation = _user_delegation(request)
        if delegation is None:
            return True
        if delegation is _NO_EMPLOYEE:
            return False  # Bug 2: mismo criterio que en ActivityAdmin
        return obj.activity.employee.delegation_id == delegation.pk

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if obj is None:
            return True
        delegation = _user_delegation(request)
        if delegation is None:
            return True
        if delegation is _NO_EMPLOYEE:
            return False  # Bug 2: mismo criterio que en ActivityAdmin
        return obj.activity.employee.delegation_id == delegation.pk

    @admin.action(description='Aprobar evidencias seleccionadas en lote')
    def approve_evidence_in_bulk(self, request, queryset):
        """Decisión 9 de decisiones.md, seguida exactamente:

        Crea una Validation NUEVA (result=True, employee=verificador
        actual, date=hoy) solo para las Evidences seleccionadas que:
          (a) no tengan ya una Validation asociada, Y
          (b) tengan archivo cargado.
        Ambos casos que no cumplen se EXCLUYEN del procesamiento y se
        reportan por separado en el mensaje — nunca se hace
        update_or_create sobre una Validation existente (pisaría un
        resultado previo, ej. un rechazo, sin dejar rastro).

        Antes aprobar_evidencias_en_lote (Decisión 13: renombrado a
        inglés).

        NOTA — Decisión 9-bis (decisiones.md): además de crear la
        Validation, esta acción marca Evidence.review_status =
        'Aprobada' en las evidencias efectivamente procesadas. Las
        evidencias EXCLUIDAS (ya validadas o sin archivo) no tocan
        review_status bajo ningún motivo.

        NOTA — restricción por grupo Verificador (Decisión 6/9): esta
        acción todavía NO valida en Fase 5 que request.user pertenezca al
        grupo Verificador. Eso es explícitamente Fase 6
        (Plan_Proyecto_SGR_Fusionado.md, sección Fase 6, punto 3). En Fase
        5 la acción es funcional para cualquier staff con permiso de
        cambiar Evidence; la restricción de grupo se agrega ENCIMA de este
        mismo método en Fase 6, no reemplazándolo.
        """
        # --- Fase 6, Paso 4a: restricción de rol ---
        # Bypass de Administrador/superuser vía _unrestricted(): sin esto,
        # admin_sgr (que el seed no agrega al grupo Verificador) quedaría
        # bloqueado para ejecutar esta acción, contradiciendo la Decisión 6.
        if not (_is_verifier(request) or _unrestricted(request)):
            self.message_user(
                request,
                "Solo el grupo Verificador puede ejecutar esta acción.",
                level=messages.ERROR,
            )
            return

        # request.user.employee puede lanzar RelatedObjectDoesNotExist
        # si un User sin fila Employee ejecuta la acción (Decisión 6,
        # caso borde). El seed de Fase 3 cubre a los 3 usuarios de prueba,
        # pero un superuser creado manualmente vía createsuperuser durante
        # debugging no tendría Employee propio.
        if not hasattr(request.user, 'employee'):
            self.message_user(
                request,
                "Tu usuario no tiene un Employee asociado, por lo que "
                "no puede quedar registrado como verificador de la "
                "Validation. Pide que se cree tu fila de Employee "
                "antes de usar esta acción.",
                level=messages.ERROR,
            )
            return

        verifier = request.user.employee

        already_validated = []
        without_file = []
        processed = []

        for evidence in queryset:
            # hasattr, no evidence.validation is None: Validation.evidence
            # es OneToOneField -> acceder al atributo inverso sin fila
            # relacionada lanza RelatedObjectDoesNotExist, no devuelve None
            # (mismo patrón de caso borde que Decisión 6, aplicado aquí a
            # Evidence.validation en vez de a User.employee).
            if hasattr(evidence, 'validation'):
                already_validated.append(evidence.code)
                continue
            if not evidence.file:
                without_file.append(evidence.code)
                continue

            Validation.objects.create(
                evidence=evidence,
                employee=verifier,
                decision='Aprobada',
                date=date.today(),
                result=True,
            )
            # Decisión 9-bis (ver docstring): solo las procesadas cambian
            # review_status. Las excluidas quedan intactas.
            evidence.review_status = 'Aprobada'
            evidence.save(update_fields=['review_status'])
            processed.append(evidence.code)

        parts = [f"{len(processed)} evidencia(s) aprobada(s)."]
        if already_validated:
            parts.append(
                f"{len(already_validated)} omitida(s) por ya tener validación: "
                f"{', '.join(already_validated)}."
            )
        if without_file:
            parts.append(
                f"{len(without_file)} omitida(s) por no tener archivo "
                f"cargado: {', '.join(without_file)}."
            )

        level = messages.SUCCESS if processed else messages.WARNING
        self.message_user(request, ' '.join(parts), level=level)


@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('id', 'evidence', 'employee', 'decision', 'result', 'date', 'version')
    search_fields = ('evidence__code', 'employee__name', 'notes')
    list_filter = ('decision', 'result', 'date')
    ordering = ('-date',)
    list_select_related = ('evidence', 'employee')

    # --- Fase 6, scoping por Delegación y restricción de rol Verificador ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        delegation = _user_delegation(request)
        if delegation is None:
            return qs
        if delegation is _NO_EMPLOYEE:
            # Bug 2: ver comentario equivalente en ActivityAdmin.get_queryset.
            return qs.none()
        return qs.filter(evidence__activity__employee__delegation=delegation)

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        return _is_verifier(request) or _unrestricted(request)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if not (_is_verifier(request) or _unrestricted(request)):
            return False
        if obj is None:
            return True
        delegation = _user_delegation(request)
        if delegation is None:
            return True
        if delegation is _NO_EMPLOYEE:
            return False  # Bug 2: mismo criterio que en ActivityAdmin/EvidenceAdmin
        return obj.evidence.activity.employee.delegation_id == delegation.pk

    def has_delete_permission(self, request, obj=None):
        # Decisión de diseño (Decisión 12, decisiones.md): no se permite
        # borrar Validation desde el Admin, ni siquiera a Administrador.
        # Coherente con la política PROTECT / conservar historial de la
        # Decisión 8 y con la razón de ser de la Decisión 9 (nunca perder
        # el rastro de una revisión ya emitida: por eso la acción de
        # Fase 5 usa create() y nunca update_or_create).
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Sin esto, el desplegable de "Evidence" en
        # /admin/performance/validation/add/ mostraba TODAS las Evidences
        # de ambas Delegaciones, y has_add_permission no alcanza a impedir
        # que un Verificador cree una Validation sobre una Evidence ajena a
        # su Delegación (has_add_permission solo valida rol, no delegación,
        # porque en el alta todavía no existe un `obj` contra qué
        # comparar). Se filtra acá, que es el único lugar del que se
        # dispone de la Evidence concreta antes de guardar.
        if db_field.name == "evidence":
            delegation = _user_delegation(request)
            if delegation is _NO_EMPLOYEE:
                # Bug 2: sin Delegación contra qué comparar -> no se ofrece
                # ninguna Evidence en el desplegable (coherente con que
                # has_add_permission ya debería bloquear a este usuario
                # salvo que además sea Verificador; si lo es igual no
                # tiene Delegación propia con la que filtrar, así que no
                # hay conjunto seguro de Evidences que mostrarle).
                kwargs["queryset"] = Evidence.objects.none()
            elif delegation is not None:
                kwargs["queryset"] = Evidence.objects.filter(
                    activity__employee__delegation=delegation
                )
        # Corrección (Fase 6, Paso 4c): mismo problema que "evidence" de
        # arriba, pero para "employee" -- sin esto, cualquier Verificador
        # podía asignar la Validation a un Employee ajeno a su Delegación
        # (o que ni siquiera pertenece al grupo Verificador), porque
        # has_add_permission solo valida rol y formfield_for_foreignkey no
        # tocaba este campo. Se filtra a Employees que pertenecen al
        # grupo Verificador y, si el usuario tiene Delegación propia, a
        # los de esa misma Delegación.
        if db_field.name == "employee":
            kwargs["queryset"] = Employee.objects.filter(
                user__groups__name="Verificador"
            ).distinct()
            delegation = _user_delegation(request)
            if delegation is _NO_EMPLOYEE:
                # Bug 2: mismo criterio que "evidence" arriba -- sin
                # Delegación propia no hay subconjunto seguro de
                # Employees-Verificador que ofrecer.
                kwargs["queryset"] = kwargs["queryset"].none()
            elif delegation is not None:
                kwargs["queryset"] = kwargs["queryset"].filter(
                    delegation=delegation
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
