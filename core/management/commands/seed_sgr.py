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
"""

from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Actividad,
    Cargo,
    Delegacion,
    Evidencia,
    Funcionario,
    Periodo,
    Validacion,
)

User = get_user_model()

GRUPOS = ["Administrador", "Delegado", "Funcionario", "Verificador"]

# Fase 6 (ajuste de seed): permisos de modelo Django por grupo. Necesarios
# porque ModelAdmin.has_add_permission() / has_change_permission() /
# has_view_permission() de Django SIEMPRE exigen request.user.has_perm(...)
# como primer chequeo (super().has_*_permission()), ANTES de que corra
# cualquier lógica de rol o Delegación de Fase 6. Sin estos permisos en el
# grupo, _es_verificador(request) puede devolver True y aun así
# ValidacionAdmin.has_add_permission() devuelve False, porque el super()
# ya cortó el paso. admin_sgr no necesita entrada aquí: es superuser en el
# seed y Django le concede todos los permisos automáticamente; se
# incluye explícitamente para Administrador de todas formas, por la misma
# razón de robustez que ya motiva _sin_restriccion() en admin.py (Decisión
# 6: un Administrador que no fuera también superuser técnico debe quedar
# igual de habilitado).
PERMISOS_POR_GRUPO = {
    "Administrador": [
        ("core", "view_actividad"), ("core", "add_actividad"),
        ("core", "change_actividad"), ("core", "delete_actividad"),
        ("core", "view_evidencia"), ("core", "add_evidencia"),
        ("core", "change_evidencia"), ("core", "delete_evidencia"),
        ("core", "view_validacion"), ("core", "add_validacion"),
        ("core", "change_validacion"),
        # delete_validacion deliberadamente excluido: ValidacionAdmin.
        # has_delete_permission() (Fase 6 / Decisión 12) devuelve False
        # para todos sin excepción, así que este permiso nunca se ejerce
        # y no se otorga aunque el usuario sea Administrador.
    ],
    "Funcionario": [
        # Ve y edita sus propias Actividades/Evidencias (get_queryset ya
        # filtra por Delegación en Fase 6); no crea ni borra ninguna de
        # las dos desde el Admin, y no tiene ningún permiso sobre
        # Validacion (Decisión 6: fuera del grupo Verificador, sin
        # acceso a Validacion en absoluto).
        ("core", "view_actividad"), ("core", "change_actividad"),
        ("core", "view_evidencia"), ("core", "change_evidencia"),
    ],
    "Verificador": [
        # Mismo acceso de lectura/edición que Funcionario sobre
        # Actividad/Evidencia (necesita verlas para poder aprobar
        # evidencias), más alta y edición de Validacion -- sin
        # delete_validacion, mismo motivo que en Administrador arriba.
        ("core", "view_actividad"), ("core", "change_actividad"),
        ("core", "view_evidencia"), ("core", "change_evidencia"),
        ("core", "view_validacion"), ("core", "add_validacion"),
        ("core", "change_validacion"),
    ],
    # "Delegado": sin permisos de modelo asignados en esta fase -- el plan
    # y la Decisión 6 no definen todavía qué puede hacer este rol en el
    # Admin; se deja el grupo creado (ya lo hacía Fase 3) pero vacío de
    # permisos, en vez de inventar un alcance no pedido.
}

SEED_FILES_DIR = Path(settings.BASE_DIR) / "core" / "fixtures" / "seed_files"

# Decision 4 -- valores de ejemplo ya definidos en decisiones.md, no inventar otros
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
            actividades = self._crear_actividades(usuarios, periodo)
            evidencias = self._crear_evidencias(actividades)
            self._crear_validaciones(evidencias, usuarios)

        self.stdout.write(self.style.SUCCESS("Seed completado."))
        self._resumen(password)

    # ------------------------------------------------------------------
    # Grupos -- plan Fase 3: "antes de crear usuarios"
    #
    # Fase 6 (ajuste): además de crear el Group, se le asignan los
    # permisos de modelo de PERMISOS_POR_GRUPO. Sin esto, has_add_permission
    # / has_change_permission de Fase 6 en EvidenciaAdmin/ValidacionAdmin
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
        # deriva del codename ("view_validacion" -> "validacion") en vez
        # de mantener una tabla aparte, porque Django genera los
        # codenames de permisos por defecto con este mismo patrón fijo
        # ("<accion>_<modelo_en_minusculas>") y no hay excepciones a esa
        # regla entre los permisos que este comando asigna.
        return codename.split("_", 1)[1]

    # ------------------------------------------------------------------
    # Delegaciones -- al menos 2, ficticias (plan: "el documento SGR §2.1
    # prohíbe datos reales"). Delegacion.id es PK natural string (Decision 11).
    # ------------------------------------------------------------------
    def _crear_delegaciones(self):
        datos = [
            dict(id="DEL-001", nombre="Delegación Centro", ambito="Urbano"),
            dict(id="DEL-002", nombre="Delegación Norte", ambito="Rural"),
        ]
        delegaciones = {}
        for d in datos:
            delegacion, creado = Delegacion.objects.get_or_create(id=d["id"], defaults=d)
            delegaciones[d["id"]] = delegacion
            self._log("Delegación", f'{d["id"]} ({d["nombre"]})', creado)
        return delegaciones

    # ------------------------------------------------------------------
    # Cargos
    # ------------------------------------------------------------------
    def _crear_cargos(self):
        nombres = ["Encargado de Delegación", "Funcionario Municipal", "Verificador de Evidencias"]
        cargos = {}
        for nombre in nombres:
            cargo, creado = Cargo.objects.get_or_create(nombre=nombre)
            cargos[nombre] = cargo
            self._log("Cargo", nombre, creado)
        return cargos

    # ------------------------------------------------------------------
    # Usuarios -- Decision 5 (los 3 exactos) + Decision 6 (Funcionario
    # propio del Administrador, capa 1 del caso borde de request.user.funcionario)
    #
    # NOTA: Funcionario.nombre es CharField obligatorio (sin default) en el
    # models.py real -- se agrega explícito en los 3 bloques de abajo. En la
    # version anterior de este comando faltaba en los 3 y habria fallado con
    # NOT NULL constraint failed: core_funcionario.nombre justo despues de
    # resolver el bug de Evidencia.fecha.
    # ------------------------------------------------------------------
    def _crear_usuarios(self, password, grupos, delegaciones, cargos):
        deleg_centro = delegaciones["DEL-001"]
        deleg_norte = delegaciones["DEL-002"]

        # --- Administrador: superuser + Funcionario propio (Decision 6) ---
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

        admin_funcionario, creado = Funcionario.objects.get_or_create(
            user=admin_user,
            defaults=dict(
                id_institucional="FUNC-ADMIN-001",
                nombre="Administrador General SGR",
                delegacion=deleg_centro,
                cargo=cargos["Encargado de Delegación"],
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

        funcionario_demo, creado = Funcionario.objects.get_or_create(
            user=func_user,
            defaults=dict(
                id_institucional="FUNC-DEMO-001",
                nombre="Funcionario Demo Norte",
                delegacion=deleg_norte,
                cargo=cargos["Funcionario Municipal"],
            ),
        )
        self._log("Funcionario", "FUNC-DEMO-001", creado)

        # --- Verificador de prueba (Decision 5: staff, grupo Verificador;
        # Decision 6 no exige Funcionario propio para este rol -- solo lo
        # exige explícitamente para el Administrador. Se crea igual aquí
        # porque Actividad.funcionario y el resto de la cadena de scoping
        # de Fase 6 pasan por Funcionario, y sin fila propia el Verificador
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

        verificador_funcionario, creado = Funcionario.objects.get_or_create(
            user=verif_user,
            defaults=dict(
                id_institucional="FUNC-VERIF-001",
                nombre="Verificador Demo Centro",
                delegacion=deleg_centro,
                cargo=cargos["Verificador de Evidencias"],
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
    # Periodo -- FK obligatoria de Actividad (Decision 1)
    # ------------------------------------------------------------------
    def _crear_periodo(self):
        # Campos reales de tu Periodo (no nombre/fecha_inicio/fecha_termino/estado bool):
        # inicio, termino, dias_computables, estado (CharField), umbral_ambar,
        # umbral_colectivo, version_parametros.
        periodo, creado = Periodo.objects.get_or_create(
            inicio=date(2026, 7, 1),
            termino=date(2026, 12, 31),
            defaults=dict(
                dias_computables=184,
                estado="Vigente",
                umbral_ambar=70.00,
                umbral_colectivo=85.00,
                version_parametros=1,
            ),
        )
        self._log("Periodo", f"{periodo.inicio} a {periodo.termino}", creado)
        return periodo

    # ------------------------------------------------------------------
    # Actividades -- repartidas entre las 2 delegaciones (via funcionario),
    # usando SOLO los valores normalizados de Decision 4 en los 4 campos
    # de texto libre, para no ensuciar list_filter en Fase 4.
    # related_name real: Actividad.funcionario (Decision 10) -- no "autor".
    # Campo real de solicitud: solicitud_problema (no "solicitud"). accion
    # y estado son obligatorios sin default en tu modelo -- se agregan aqui.
    # ------------------------------------------------------------------
    def _crear_actividades(self, usuarios, periodo):
        datos = [
            dict(
                funcionario=usuarios["admin_funcionario"],
                periodo=periodo,
                fecha=date(2026, 8, 5),
                tipo_actividad=TIPO_ACTIVIDAD[0],
                servicio=SERVICIO[0],
                atencion=TIPO_ATENCION[0],
                subatencion=SUB_ATENCION[0],
                solicitud_problema="Solicitud de informe social — sector centro",
                accion="Se recopilan antecedentes y se elabora informe social.",
                estado="Pendiente",
            ),
            dict(
                funcionario=usuarios["funcionario_demo"],
                periodo=periodo,
                fecha=date(2026, 8, 12),
                tipo_actividad=TIPO_ACTIVIDAD[1],
                servicio=SERVICIO[1],
                atencion=TIPO_ATENCION[1],
                subatencion=SUB_ATENCION[1],
                solicitud_problema="Seguimiento de subsidio — sector norte",
                accion="Se realiza seguimiento telefónico del estado del subsidio.",
                estado="Pendiente",
            ),
        ]
        actividades = []
        for d in datos:
            actividad, creado = Actividad.objects.get_or_create(
                funcionario=d["funcionario"],
                fecha=d["fecha"],
                solicitud_problema=d["solicitud_problema"],
                defaults=d,
            )
            actividades.append(actividad)
            self._log("Actividad", d["solicitud_problema"], creado)
        return actividades

    # ------------------------------------------------------------------
    # Evidencias -- FileField real (Decision 7). Evidencia.codigo es PK
    # natural string (Decision 11) -- se asigna explícito, no autogenerado.
    #
    # NOTA: Evidencia.fecha es DateField obligatorio (sin default) en el
    # models.py real -- se agrega explícito como fecha=actividad.fecha
    # (la evidencia se sube el mismo día de la actividad). Este era el bug
    # original reportado: NOT NULL constraint failed: core_evidencia.fecha.
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
            evidencia, creado = Evidencia.objects.get_or_create(
                codigo=codigo,
                defaults=dict(
                    actividad=actividad,
                    fecha=actividad.fecha,
                    estado_revision="Pendiente",
                ),
            )
            if creado:
                ruta = SEED_FILES_DIR / nombre_archivo
                with ruta.open("rb") as f:
                    evidencia.archivo.save(nombre_archivo, File(f), save=True)
            evidencias.append(evidencia)
            self._log("Evidencia", codigo, creado)
        return evidencias

    # ------------------------------------------------------------------
    # Validaciones -- al menos 1, para demostrar ValidacionInline en Fase 5.
    # related_name real: Validacion.evidencia -> "validacion" (singular,
    # relacion 1:0..1, Decision 3/10). Validacion.funcionario -> el
    # verificador (Decision 8: Validacion.evidencia usa CASCADE, no PROTECT).
    #
    # Fase 6 (ajuste de seed, Bug 1): se valida evidencias[1] (EVID-002,
    # Actividad de funcionario_demo, Delegación Norte) en vez de
    # evidencias[0] como en la versión original. Motivo: verificador_demo
    # pertenece a Delegación Centro (ver _crear_usuarios), y el scoping por
    # Delegación de Fase 6 (Decisión 6) hace que EvidenciaAdmin.get_queryset
    # solo le muestre Evidencias de Centro -- es decir, solo EVID-001. Si
    # esa fuera la que ya queda validada acá, verificador_demo no tendría
    # ninguna Evidencia pendiente visible para probar en vivo la acción
    # "aprobar evidencias en lote" (Decisión 9): el único caso de éxito
    # real quedaría fuera de lo que su propio scoping le permite ver.
    # Validando en cambio EVID-002 (Norte), EVID-001 (Centro) queda
    # pendiente y demostrable con verificador_demo tal como pide la
    # Decisión 9 ("Sirve también para demostrar en vivo el criterio de
    # seguridad"). No se agrega una tercera Evidencia ni se toca qué
    # Delegaciones/usuarios existen -- solo cuál de las dos evidencias ya
    # creadas queda con Validación previa.
    #
    # Nota: esta Validación de EVID-002 (Norte) queda con funcionario =
    # verificador_funcionario (Centro), igual que la versión original del
    # seed dejaba la de EVID-001 (Centro) con ese mismo verificador. El
    # scoping por Delegación de Fase 6 (Decisión 6) rige las acciones
    # hechas EN VIVO a través del Django Admin -- ValidacionAdmin.
    # formfield_for_foreignkey / has_add_permission -- no una restricción
    # a nivel de base de datos sobre Validacion.funcionario; este dato de
    # prueba se crea directo por ORM en el seed, igual que el resto del
    # comando, y representa simplemente el historial ya existente al
    # momento en que arranca la demo.
    # ------------------------------------------------------------------
    def _crear_validaciones(self, evidencias, usuarios):
        if len(evidencias) < 2:
            # Con 0 o 1 Evidencia no hay una segunda que validar sin dejar
            # a verificador_demo sin ningún caso pendiente en Centro; se
            # omite en vez de forzar el mismo problema que este ajuste
            # busca resolver (ver bloque de comentario arriba).
            return
        evidencia_a_validar = evidencias[1]
        validacion, creado = Validacion.objects.get_or_create(
            evidencia=evidencia_a_validar,
            defaults=dict(
                funcionario=usuarios["verificador_funcionario"],
                fecha=date(2026, 8, 20),
                decision="Aprobada",
                resultado=True,
                observacion="Evidencia conforme al respaldo solicitado.",
                version=1,
            ),
        )
        self._log("Validación", f"para {evidencia_a_validar.codigo}", creado)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _log(self, tipo, nombre, creado):
        marca = "creado" if creado else "ya existía"
        self.stdout.write(f"  [{tipo}] {nombre} — {marca}")

    def _resumen(self, password):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Cuentas de prueba (Decision 5):")
        self.stdout.write(f"  admin_sgr         / {password}  (superuser, grupo Administrador)")
        self.stdout.write(f"  funcionario_demo  / {password}  (grupo Funcionario)")
        self.stdout.write(f"  verificador_demo  / {password}  (grupo Verificador)")
        self.stdout.write("=" * 60)