"""
Comando de seed idempotente para datos de prueba del SGR (Fase 3).

Uso:
    python manage.py seed_sgr

Reset soportado (Decision 8, pendiente de Fase 3): NO borrar filas sueltas desde
el Admin -- el on_delete=PROTECT por defecto va a bloquear casi cualquier borrado
en cascada. El unico reset soportado es:

    Remove-Item db.sqlite3
    python manage.py migrate
    python manage.py seed_sgr

Este comando es idempotente (Decision 8, via get_or_create): correrlo varias
veces sobre la misma base no duplica registros ni choca con PROTECT.

Movido de core/management/commands/ a performance/management/commands/
(Decisión 13: renombrado a inglés + separación en apps). Vive en
`performance` y no en `organization` porque este comando ya depende de
`organization.models` (Employee/Delegation/Position) para poder crear
Activity/Evidence/Validation -- ponerlo en `organization` habría invertido
esa dependencia (organization importando de performance), rompiendo la
separación de responsabilidades de la Decisión 13.
"""

from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from organization.models import Delegation, Employee, Position
from performance.models import Activity, CatalogItem, Evidence, Period, Validation

User = get_user_model()

GRUPOS = ["Administrador", "Delegado", "Funcionario", "Verificador"]

# Fase 6 (ajuste de seed): permisos de modelo Django por grupo. Necesarios
# porque ModelAdmin.has_add_permission() / has_change_permission() /
# has_view_permission() de Django SIEMPRE exigen request.user.has_perm(...)
# como primer chequeo (super().has_*_permission()), ANTES de que corra
# cualquier lógica de rol o Delegación de Fase 6. Sin estos permisos en el
# grupo, _is_verifier(request) puede devolver True y aun así
# ValidationAdmin.has_add_permission() devuelve False, porque el super()
# ya cortó el paso. admin_sgr no necesita entrada aquí: es superuser en el
# seed y Django le concede todos los permisos automáticamente; se
# incluye explícitamente para Administrador de todas formas, por la misma
# razón de robustez que ya motiva _unrestricted() en admin.py (Decisión
# 6: un Administrador que no fuera también superuser técnico debe quedar
# igual de habilitado).
#
# Nota (Decisión 13): app_label cambia de "core" a "performance" para
# estos tres modelos tras la separación en apps -- Activity/Evidence/
# Validation viven ahora en performance/models.py, no en core/models.py.
PERMISOS_POR_GRUPO = {
    "Administrador": [
        ("performance", "view_activity"), ("performance", "add_activity"),
        ("performance", "change_activity"), ("performance", "delete_activity"),
        ("performance", "view_evidence"), ("performance", "add_evidence"),
        ("performance", "change_evidence"), ("performance", "delete_evidence"),
        ("performance", "view_validation"), ("performance", "add_validation"),
        ("performance", "change_validation"),
        # Fase 3 (Decisión 20): delete_validation y delete_commitment se
        # otorgan SOLO a Administrador, el mismo criterio que ya tienen
        # delete_activity y delete_evidence. Antes estaban excluidos porque
        # el borrado era físico (Decisiones 12 y 18); ahora es lógico
        # (deleted_at) y no destruye el rastro. Funcionario y Verificador
        # siguen sin permiso de borrar.
        ("performance", "delete_validation"),
        #
        # Fase 2 (patch 5, Decisión 18): Commitment.
        ("performance", "view_commitment"), ("performance", "add_commitment"),
        ("performance", "change_commitment"), ("performance", "delete_commitment"),
        # CatalogItem y Meta: solo Administrador (Decisión 18). La Guía
        # (sección 3) asigna al Administrador "catálogos, metas y
        # ponderaciones" como responsabilidad propia.
        ("performance", "view_catalogitem"), ("performance", "add_catalogitem"),
        ("performance", "change_catalogitem"), ("performance", "delete_catalogitem"),
        ("performance", "view_meta"), ("performance", "add_meta"),
        ("performance", "change_meta"), ("performance", "delete_meta"),
    ],
    "Funcionario": [
        # Ve y edita sus propias Activities/Evidences (get_queryset ya
        # filtra por Delegación en Fase 6); no crea ni borra ninguna de
        # las dos desde el Admin, y no tiene ningún permiso sobre
        # Validation (Decisión 6: fuera del grupo Verificador, sin
        # acceso a Validation en absoluto).
        ("performance", "view_activity"), ("performance", "change_activity"),
        ("performance", "view_evidence"), ("performance", "change_evidence"),
        # Fase 2 (patch 5, Decisión 18): Commitment. La Guía asigna al
        # Funcionario registrar compromisos (HU-12) y actualizar su
        # estado (HU-13) -> view + add + change. Sin delete (Decisión 20:
        # el borrado lógico es solo de Administrador). El acotamiento a su
        # propia Delegación NO depende de estos permisos: lo impone
        # CommitmentAdmin.
        ("performance", "view_commitment"), ("performance", "add_commitment"),
        ("performance", "change_commitment"),
    ],
    "Verificador": [
        # Mismo acceso de lectura/edición que Funcionario sobre
        # Activity/Evidence (necesita verlas para poder aprobar
        # evidencias), más alta y edición de Validation -- sin
        # delete_validation (Decisión 20: solo Administrador).
        ("performance", "view_activity"), ("performance", "change_activity"),
        ("performance", "view_evidence"), ("performance", "change_evidence"),
        ("performance", "view_validation"), ("performance", "add_validation"),
        ("performance", "change_validation"),
    ],
    # "Verificador": sin permisos sobre Commitment (Decisión 18). La Guía
    # le asigna revisar evidencias y validar o rechazar registros; un
    # compromiso no es una evidencia.
    #
    # "Delegado": sin permisos de modelo asignados en esta fase -- el plan
    # y la Decisión 6 no definen todavía qué puede hacer este rol en el
    # Admin; se deja el grupo creado (ya lo hacía Fase 3) pero vacío de
    # permisos, en vez de inventar un alcance no pedido. La Decisión 18
    # documenta por qué tampoco se crea un usuario delegado_demo ahora:
    # la reasignación de responsable (HU-15, P2) es su única diferencia
    # real frente a Funcionario y queda fuera del alcance formativo.
}

# Movido de core/fixtures/seed_files a performance/fixtures/seed_files
# (Decisión 13): los archivos de ejemplo viajan con la app dueña de Evidence.
SEED_FILES_DIR = Path(settings.BASE_DIR) / "performance" / "fixtures" / "seed_files"

# Decision 4 -- valores de ejemplo ya definidos en decisiones.md, no inventar otros.
#
# Fase 2 (paso 2.1): TIPO_ATENCION ya NO se asigna directo como texto en
# Activity.attention -- ese campo pasó a ser FK hacia CatalogItem. Los
# nombres se mantienen acá igual (siguen siendo los valores de negocio
# válidos, ver Decision 4) y se resuelven a su CatalogItem correspondiente
# en _crear_catalogo_atencion(), reutilizando el mismo patrón de
# get_or_create() que usa la migración de datos 0003 para no duplicar
# filas del catálogo.
TIPO_ATENCION = ["Informes Sociales", "Gestión de Subsidios", "Derivación"]
SUB_ATENCION = ["Informe Aporte Económico", "Orientación Social", "PGU"]
SERVICIO = ["Atención Presencial", "Atención Telefónica"]
TIPO_ACTIVIDAD = ["Primera Atención", "Seguimiento"]


class Command(BaseCommand):
    help = "Crea datos de prueba reproducibles para el SGR (Fase 3)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="sgr-demo-2026",
            help="Password para los 3 usuarios de prueba (default: sgr-demo-2026).",
        )

    def handle(self, *args, **options):
        password = options["password"]

        with transaction.atomic():
            grupos = self._crear_grupos()
            delegaciones = self._crear_delegaciones()
            cargos = self._crear_cargos()
            usuarios = self._crear_usuarios(password, grupos, delegaciones, cargos)
            periodo = self._crear_periodo()
            catalogo_atencion = self._crear_catalogo_atencion()
            actividades = self._crear_actividades(usuarios, periodo, catalogo_atencion)
            evidencias = self._crear_evidencias(actividades)
            self._crear_validaciones(evidencias, usuarios)

        self.stdout.write(self.style.SUCCESS("Seed completado."))
        self._resumen(password)

    # ------------------------------------------------------------------
    # Grupos -- plan Fase 3: "antes de crear usuarios"
    #
    # Fase 6 (ajuste): además de crear el Group, se le asignan los
    # permisos de modelo de PERMISOS_POR_GRUPO. Sin esto, has_add_permission
    # / has_change_permission de Fase 6 en EvidenceAdmin/ValidationAdmin
    # bloquean a Funcionario/Verificador en el chequeo base de Django
    # (super().has_*_permission()), antes de que la lógica de rol y
    # Delegación de Fase 6 llegue siquiera a evaluarse -- ver comentario
    # junto a PERMISOS_POR_GRUPO más arriba.
    # ------------------------------------------------------------------
    def _crear_grupos(self):
        grupos = {}
        for nombre in GRUPOS:
            grupo, creado = Group.objects.get_or_create(name=nombre)
            grupos[nombre] = grupo
            self._log("Grupo", nombre, creado)
            self._asignar_permisos(grupo, PERMISOS_POR_GRUPO.get(nombre, []))
        return grupos

    def _asignar_permisos(self, grupo, permisos):
        # group.permissions.add() es idempotente por sí solo (ManyToMany:
        # agregar una relación ya existente no la duplica), consistente
        # con el resto del comando (Decisión 8: correrlo varias veces no
        # debe cambiar el resultado). Se usa get_by_natural_key() en vez
        # de una query manual por content_type + codename porque es la
        # forma estándar de Django de resolver un Permission conociendo
        # (app_label, codename) sin tener que buscar antes el ContentType.
        for app_label, codename in permisos:
            permiso = Permission.objects.get_by_natural_key(
                codename, app_label, self._modelo_de(codename)
            )
            grupo.permissions.add(permiso)

    @staticmethod
    def _modelo_de(codename):
        # Permission.objects.get_by_natural_key(codename, app_label, model)
        # exige el nombre del modelo en minúsculas por separado -- se
        # deriva del codename ("view_validation" -> "validation") en vez
        # de mantener una tabla aparte, porque Django genera los
        # codenames de permisos por defecto con este mismo patrón fijo
        # ("<accion>_<modelo_en_minusculas>") y no hay excepciones a esa
        # regla entre los permisos que este comando asigna.
        return codename.split("_", 1)[1]

    # ------------------------------------------------------------------
    # Delegaciones -- al menos 2, ficticias (plan: "el documento SGR §2.1
    # prohíbe datos reales"). Delegation.id es PK natural string (Decision 11).
    # ------------------------------------------------------------------
    def _crear_delegaciones(self):
        datos = [
            dict(id="DEL-001", name="Delegación Centro", scope="Urbano"),
            dict(id="DEL-002", name="Delegación Norte", scope="Rural"),
        ]
        delegaciones = {}
        for d in datos:
            delegacion, creado = Delegation.objects.get_or_create(id=d["id"], defaults=d)
            delegaciones[d["id"]] = delegacion
            self._log("Delegación", f'{d["id"]} ({d["name"]})', creado)
        return delegaciones

    # ------------------------------------------------------------------
    # Cargos
    # ------------------------------------------------------------------
    def _crear_cargos(self):
        nombres = ["Encargado de Delegación", "Funcionario Municipal", "Verificador de Evidencias"]
        cargos = {}
        for nombre in nombres:
            cargo, creado = Position.objects.get_or_create(name=nombre)
            cargos[nombre] = cargo
            self._log("Cargo", nombre, creado)
        return cargos

    # ------------------------------------------------------------------
    # Usuarios -- Decision 5 (los 3 exactos) + Decision 6 (Employee
    # propio del Administrador, capa 1 del caso borde de
    # request.user.employee)
    #
    # NOTA: Employee.name es CharField obligatorio (sin default) en el
    # models.py real -- se agrega explícito en los 3 bloques de abajo.
    # ------------------------------------------------------------------
    def _crear_usuarios(self, password, grupos, delegaciones, cargos):
        deleg_centro = delegaciones["DEL-001"]
        deleg_norte = delegaciones["DEL-002"]

        # --- Administrador: superuser + Employee propio (Decision 6) ---
        admin_user, creado = User.objects.get_or_create(
            username="admin_sgr",
            defaults=dict(email="admin@sgr.local", is_staff=True, is_superuser=True),
        )
        if creado:
            admin_user.set_password(password)
        # get_or_create solo aplica defaults al CREAR -- si ya existia de una
        # corrida anterior con otro valor, is_staff/is_superuser no se
        # actualizan solos. Se fuerza en cada corrida para que el seed sea
        # idempotente tambien en el ESTADO final, no solo en no duplicar filas.
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        admin_user.groups.add(grupos["Administrador"])
        self._log("Usuario", "admin_sgr (superuser)", creado)

        admin_funcionario, creado = Employee.objects.get_or_create(
            user=admin_user,
            defaults=dict(
                institutional_id="FUNC-ADMIN-001",
                name="Administrador General SGR",
                delegation=deleg_centro,
                position=cargos["Encargado de Delegación"],
            ),
        )
        self._log("Funcionario (admin)", "FUNC-ADMIN-001", creado)

        # --- Funcionario de prueba (Delegación Norte, para tener las 2
        # delegaciones cubiertas desde el primer momento) ---
        func_user, creado = User.objects.get_or_create(
            username="funcionario_demo",
            defaults=dict(email="funcionario@sgr.local", is_staff=True),
        )
        if creado:
            func_user.set_password(password)
        func_user.is_staff = True
        func_user.save()
        func_user.groups.add(grupos["Funcionario"])
        self._log("Usuario", "funcionario_demo", creado)

        funcionario_demo, creado = Employee.objects.get_or_create(
            user=func_user,
            defaults=dict(
                institutional_id="FUNC-DEMO-001",
                name="Funcionario Demo Norte",
                delegation=deleg_norte,
                position=cargos["Funcionario Municipal"],
            ),
        )
        self._log("Funcionario", "FUNC-DEMO-001", creado)

        # --- Verificador de prueba (Decision 5: staff, grupo Verificador;
        # Decision 6 no exige Employee propio para este rol -- solo lo
        # exige explícitamente para el Administrador. Se crea igual aquí
        # porque Activity.employee y el resto de la cadena de scoping
        # de Fase 6 pasan por Employee, y sin fila propia el Verificador
        # no tendría delegación con la que operar en esa fase) ---
        verif_user, creado = User.objects.get_or_create(
            username="verificador_demo",
            defaults=dict(email="verificador@sgr.local", is_staff=True),
        )
        if creado:
            verif_user.set_password(password)
        verif_user.is_staff = True
        verif_user.save()
        verif_user.groups.add(grupos["Verificador"])
        self._log("Usuario", "verificador_demo", creado)

        verificador_funcionario, creado = Employee.objects.get_or_create(
            user=verif_user,
            defaults=dict(
                institutional_id="FUNC-VERIF-001",
                name="Verificador Demo Centro",
                delegation=deleg_centro,
                position=cargos["Verificador de Evidencias"],
            ),
        )
        self._log("Funcionario (verificador)", "FUNC-VERIF-001", creado)

        return {
            "admin_user": admin_user,
            "admin_funcionario": admin_funcionario,
            "func_user": func_user,
            "funcionario_demo": funcionario_demo,
            "verif_user": verif_user,
            "verificador_funcionario": verificador_funcionario,
        }

    # ------------------------------------------------------------------
    # Periodo -- FK obligatoria de Activity (Decision 1)
    # ------------------------------------------------------------------
    def _crear_periodo(self):
        # Campos reales de tu Period (no name/fecha_inicio/fecha_termino/estado bool):
        # start_date, end_date, computable_days, status (CharField),
        # amber_threshold, collective_threshold, parameters_version.
        periodo, creado = Period.objects.get_or_create(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 12, 31),
            defaults=dict(
                computable_days=184,
                status="Vigente",
                amber_threshold=70.00,
                collective_threshold=85.00,
                parameters_version=1,
            ),
        )
        self._log("Periodo", f"{periodo.start_date} a {periodo.end_date}", creado)
        return periodo

    # ------------------------------------------------------------------
    # Catálogo de Tipo Atención (Fase 2, paso 2.1) -- CatalogItem
    # reemplaza el CharField de texto libre que tenía Activity.attention.
    # get_or_create() por (category, name) es idempotente frente al
    # UniqueConstraint del modelo (Decision 8: correrlo varias veces no
    # debe fallar ni duplicar), igual patrón que el resto del comando.
    # Solo se crean acá los 2 valores que usa TIPO_ATENCION en las
    # actividades de ejemplo de abajo -- si una migración anterior (0003)
    # ya corrió sobre esta misma base y cargó el catálogo completo de la
    # Decision 4, get_or_create() no duplica nada, solo reutiliza esas
    # filas.
    # ------------------------------------------------------------------
    def _crear_catalogo_atencion(self):
        catalogo = {}
        for nombre in TIPO_ATENCION:
            item, creado = CatalogItem.objects.get_or_create(
                category=CatalogItem.CATEGORY_ATTENTION, name=nombre
            )
            catalogo[nombre] = item
            self._log("CatalogItem (attention)", nombre, creado)
        return catalogo

    # ------------------------------------------------------------------
    # Actividades -- repartidas entre las 2 delegaciones (via employee),
    # usando SOLO los valores normalizados de Decision 4 en los 4 campos
    # de clasificación, para no ensuciar list_filter en Fase 4.
    # related_name real: Activity.employee (Decision 10) -- no "autor".
    # Campo real de solicitud: request_description (no "solicitud").
    # action_taken y status son obligatorios sin default en tu modelo --
    # se agregan aqui.
    #
    # Fase 2 (paso 2.1): `attention` ya no recibe el string de
    # TIPO_ATENCION directo -- recibe el CatalogItem resuelto por
    # _crear_catalogo_atencion(), porque el campo pasó a ser FK.
    # activity_type, service y sub_attention siguen siendo texto libre sin
    # cambios (ver docstring de CatalogItem en models.py).
    # ------------------------------------------------------------------
    def _crear_actividades(self, usuarios, periodo, catalogo_atencion):
        datos = [
            dict(
                employee=usuarios["admin_funcionario"],
                period=periodo,
                date=date(2026, 8, 5),
                activity_type=TIPO_ACTIVIDAD[0],
                service=SERVICIO[0],
                attention=catalogo_atencion[TIPO_ATENCION[0]],
                sub_attention=SUB_ATENCION[0],
                request_description="Solicitud de informe social — sector centro",
                action_taken="Se recopilan antecedentes y se elabora informe social.",
                status="Pendiente",
            ),
            dict(
                employee=usuarios["funcionario_demo"],
                period=periodo,
                date=date(2026, 8, 12),
                activity_type=TIPO_ACTIVIDAD[1],
                service=SERVICIO[1],
                attention=catalogo_atencion[TIPO_ATENCION[1]],
                sub_attention=SUB_ATENCION[1],
                request_description="Seguimiento de subsidio — sector norte",
                action_taken="Se realiza seguimiento telefónico del estado del subsidio.",
                status="Pendiente",
            ),
        ]
        actividades = []
        for d in datos:
            actividad, creado, restaurado = self._get_or_restore(
                Activity,
                employee=d["employee"],
                date=d["date"],
                request_description=d["request_description"],
                defaults=d,
            )
            actividades.append(actividad)
            self._log("Actividad", d["request_description"], creado, restaurado)
        return actividades

    # ------------------------------------------------------------------
    # Evidencias -- FileField real (Decision 7). Evidence.code es PK
    # natural string (Decision 11). Desde la Decisión 33 el sistema lo genera
    # cuando no se le da uno (`Evidence.save()`); el seed lo asigna explícito
    # a propósito: son datos de demo con clave fija, y `_get_or_restore` los
    # busca por código para poder correr el comando varias veces sin duplicarlos.
    #
    # NOTA: Evidence.date es DateField obligatorio (sin default) en el
    # models.py real -- se agrega explícito como date=actividad.date
    # (la evidencia se sube el mismo día de la actividad). Este era el bug
    # original reportado: NOT NULL constraint failed: core_evidencia.fecha
    # (ahora performance_evidence.date, mismo bug ya resuelto).
    # ------------------------------------------------------------------
    def _crear_evidencias(self, actividades):
        archivos_disponibles = sorted(SEED_FILES_DIR.glob("*.pdf"))
        if not archivos_disponibles:
            self.stdout.write(
                self.style.WARNING(
                    f"No se encontraron archivos en {SEED_FILES_DIR}. "
                    "Corre el paso 2 de la guía antes de seedear evidencias."
                )
            )
            return []

        evidencias = []
        for i, actividad in enumerate(actividades, start=1):
            codigo = f"EVID-{i:03d}"
            nombre_archivo = archivos_disponibles[(i - 1) % len(archivos_disponibles)].name
            evidencia, creado, restaurado = self._get_or_restore(
                Evidence,
                code=codigo,
                defaults=dict(
                    activity=actividad,
                    date=actividad.date,
                    review_status=Evidence.REVIEW_STATUS_PENDIENTE,
                ),
            )
            if creado:
                ruta = SEED_FILES_DIR / nombre_archivo
                with ruta.open("rb") as f:
                    evidencia.file.save(nombre_archivo, File(f), save=True)
            evidencias.append(evidencia)
            self._log("Evidencia", codigo, creado, restaurado)
        return evidencias

    # ------------------------------------------------------------------
    # Validaciones -- al menos 1, para demostrar ValidationInline en Fase 5.
    # related_name real: Validation.evidence -> "validation" (singular,
    # relacion 1:0..1, Decision 3/10). Validation.employee -> el
    # verificador (Decision 8: Validation.evidence usa CASCADE, no PROTECT).
    #
    # Fase 6 (ajuste de seed, Bug 1): se valida evidencias[1] (EVID-002,
    # Actividad de funcionario_demo, Delegación Norte) en vez de
    # evidencias[0] como en la versión original. Motivo: verificador_demo
    # pertenece a Delegación Centro (ver _crear_usuarios), y el scoping por
    # Delegación de Fase 6 (Decisión 6) hace que EvidenceAdmin.get_queryset
    # solo le muestre Evidences de Centro -- es decir, solo EVID-001. Si
    # esa fuera la que ya queda validada acá, verificador_demo no tendría
    # ninguna Evidence pendiente visible para probar en vivo la acción
    # "aprobar evidencias en lote" (Decisión 9): el único caso de éxito
    # real quedaría fuera de lo que su propio scoping le permite ver.
    # Validando en cambio EVID-002 (Norte), EVID-001 (Centro) queda
    # pendiente y demostrable con verificador_demo tal como pide la
    # Decisión 9 ("Sirve también para demostrar en vivo el criterio de
    # seguridad"). No se agrega una tercera Evidence ni se toca qué
    # Delegaciones/usuarios existen -- solo cuál de las dos evidencias ya
    # creadas queda con Validación previa.
    #
    # Nota: esta Validación de EVID-002 (Norte) queda con employee =
    # verificador_funcionario (Centro), igual que la versión original del
    # seed dejaba la de EVID-001 (Centro) con ese mismo verificador. El
    # scoping por Delegación de Fase 6 (Decisión 6) rige las acciones
    # hechas EN VIVO a través del Django Admin -- ValidationAdmin.
    # formfield_for_foreignkey / has_add_permission -- no una restricción
    # a nivel de base de datos sobre Validation.employee; este dato de
    # prueba se crea directo por ORM en el seed, igual que el resto del
    # comando, y representa simplemente el historial ya existente al
    # momento en que arranca la demo.
    # ------------------------------------------------------------------
    def _crear_validaciones(self, evidencias, usuarios):
        if len(evidencias) < 2:
            # Con 0 o 1 Evidence no hay una segunda que validar sin dejar
            # a verificador_demo sin ningún caso pendiente en Centro; se
            # omite en vez de forzar el mismo problema que este ajuste
            # busca resolver (ver bloque de comentario arriba).
            return
        evidencia_a_validar = evidencias[1]
        validacion, creado, restaurado = self._get_or_restore(
            Validation,
            evidence=evidencia_a_validar,
            defaults=dict(
                employee=usuarios["verificador_funcionario"],
                date=date(2026, 8, 20),
                decision="Aprobada",
                result=True,
                notes="Evidencia conforme al respaldo solicitado.",
                version=1,
            ),
        )
        self._log("Validación", f"para {evidencia_a_validar.code}", creado, restaurado)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _get_or_restore(self, modelo, defaults=None, **lookup):
        # Decisión 20: `modelo.objects` no ve los registros eliminados
        # lógicamente, así que get_or_create() no encontraba la fila
        # escondida e intentaba crearla de nuevo (choque de clave primaria
        # o UNIQUE en Evidence/Validation, duplicado en Activity). Se busca
        # en all_objects y, si estaba eliminada, se restaura: el seed
        # significa "deja los datos de la demo presentes".
        obj, creado = modelo.all_objects.get_or_create(defaults=defaults, **lookup)
        restaurado = False
        if not creado and obj.deleted_at is not None:
            obj.restore()
            restaurado = True
        return obj, creado, restaurado

    def _log(self, tipo, nombre, creado, restaurado=False):
        if restaurado:
            marca = "restaurado"
        else:
            marca = "creado" if creado else "ya existía"
        self.stdout.write(f"  [{tipo}] {nombre} — {marca}")

    def _resumen(self, password):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Cuentas de prueba (Decision 5):")
        self.stdout.write(f"  admin_sgr         / {password}  (superuser, grupo Administrador)")
        self.stdout.write(f"  funcionario_demo  / {password}  (grupo Funcionario)")
        self.stdout.write(f"  verificador_demo  / {password}  (grupo Verificador)")
        self.stdout.write("=" * 60)
