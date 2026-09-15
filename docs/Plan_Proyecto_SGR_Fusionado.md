# Plan de trabajo — U2 Eval2 "Django Admin" (Caso SGR)

> Este plan fusiona dos versiones de trabajo previas: la estructura de fases paralelas con reparto por integrante, y el checklist granular Fase 0–9. Todo está anclado a la rúbrica real del enunciado (100 pts, 7 criterios) y al modelo de datos del caso SGR, cerrado en **7 entidades** (Delegación / Cargo / Funcionario / Período / Actividad / Evidencia / Validación) tras revisar el MER contra el diagrama de dominio completo de Actividad 3.
>
> **Documento vivo:** este plan se actualiza a medida que avanza el proyecto. El estado de cada checkbox refleja el avance real al momento de la última edición, no una proyección fija desde el inicio.

---

## 0. Cómo se organiza el trabajo (vista general)

Hay una razón concreta para no repartir las 4 personas en paralelo desde el día 1: si cada uno define
campos distintos para el mismo modelo, el merge de `models.py` se vuelve un problema serio. Por eso
las Fases 1 a 3 son **secuenciales y bloqueantes** — las hace un número reducido de personas — y recién
después de cerrar el modelo y los datos de prueba conviene dividir por persona.

```
FASE 0 → FASE 1 → FASE 2 → FASE 3   (secuenciales, bloqueantes)
Diseño    Entorno   Modelo   Datos
rápido    + BD      de datos de prueba
                                │
        ┌───────────────┬──────┴────────┬───────────────┐
        ▼               ▼               ▼               ▼
    FASE 4          FASE 5          FASE 6          FASE 7 + 8
    Admin Básico    Admin Pro       Seguridad       Informe + Git
    (paralelo)      (paralelo)      (paralelo)      (grupal, continuo desde el día 1)
        │               │               │
        └───────────────┴───────────────┘
                        │
                        ▼
                    FASE 9 (todos juntos)
                    Integración + ensayo de revisión en vivo
```

### Reparto del equipo

El criterio para armar los paquetes fue balancear puntaje + dependencia técnica, no repartir en partes
iguales. Este es el reparto real acordado por el equipo:

| Integrante     | Fase(s) a cargo                                                                                                  | Puntaje que cubre                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| **Reinaldo**   | Lidera Fases 0–3 (Setup, Modelo de 7 entidades, Seed) en solitario por ser bloqueantes                             | 9 pts (Conexión BD)                                    |
| **Maricel**    | Fase 5 (Admin Pro: Inlines, Acción personalizada, validación `clean()`)                                            | 22 pts (Admin Pro)                                     |
| **Constanza**  | Fase 4 (Admin Básico: tablas maestras, `list_display`)                                                             | 10 pts (Admin Básico)                                  |
| **Valentina**  | Fase 6 (Seguridad y Scoping: `get_queryset`, permisos)                                                              | 15 pts (Seguridad)                                     |

**Fase 7 + 8 (Informe + Git, 24 pts) son trabajo grupal**, no de una sola persona: cada integrante
documenta y comitea la parte que construyó, en paralelo desde el día 1 y a medida que su propia fase
avanza (ver el detalle en Fase 7 y Fase 8 más abajo).

La Fase 9 (Revisión en vivo, 20 pts) la hacen **los 4 juntos** al final — no está asignada a nadie en
particular porque cualquiera puede recibir la pregunta dirigida del docente.

**Importante sobre Fase 7 (Informe):** no se escribe al final ni la redacta una sola persona. Cada
integrante documenta la evidencia (capturas, fragmentos de código) de su propia fase a medida que la
construye, porque el informe pide justo eso: evidencia de cosas que van cambiando mientras se
construyen. Al final se compila en un solo PDF.

**Nota sobre la 7ª entidad (`Validación`):** no cambia el reparto — cae donde ya está el trabajo
relacionado. Reinaldo la modela en Fase 2 y la contempla en el seed de Fase 3; Maricel la conecta en
Fase 5 (Inline + validación); Valentina la contempla en el scoping de Fase 6; Constanza la registra en
el Admin básico de Fase 4 igual que ya hacía con Evidencia.

---

## Fase 0 — Recorte y diseño rápido

**Quién:** todo el equipo junto (es una decisión de diseño, no de código).

- [x] Elegir las 4 tablas maestras + 3 operativas a implementar — alcance confirmado en **7 entidades**: Delegación, Cargo, Funcionario, Período (maestras) + Actividad, Evidencia, Validación (operativas). `Validación` se agregó como entidad propia — no como campo simple `revisado_por` en Evidencia — porque el diagrama de dominio completo ya la modela así, y usar el campo simple ahora habría significado migrar datos a una tabla nueva en la próxima entrega
- [x] Definir los usuarios de prueba para la demo (mínimo Administrador + Funcionario; opcional sumar Verificador)
- [x] Confirmar el criterio de seguridad: scoping por Delegación + restricción por rol
- [x] Ajustar el diagrama ER con los tipos de datos definitivos
- [ ] Repartir las fases siguientes (ver tabla de reparto arriba, o ajustarla al equipo real)

---

## Fase 1 — Entorno y conexión a BD · *Conexión BD + Migraciones (9 pts)*

**Bloqueante.** La hizo Reinaldo; el resto revisó vía Pull Request. Ejecutada siguiendo la
guía paso a paso propia `Fase1_Entorno_y_Conexion_BD.md` (VS Code + PowerShell), que quedó documentada
para que el resto del equipo pueda repetir el proceso o revisar el porqué de cada decisión.

**Importante:** en esta fase **no** se crean los modelos del dominio (Delegación, Funcionario,
Actividad, etc.) — eso es la Fase 2. Acá solo se prueba que el proyecto migra usando las apps internas
de Django (`auth`, `admin`, `sessions`...), que ya necesitan una conexión de BD real y funcionando.

**Decisiones técnicas tomadas en esta fase** (quedaron fijadas para el resto del proyecto):

| Punto | Decisión real | Por qué |
| --- | --- | --- |
| Motor de BD | **SQLite** | Indicado por el profesor en clases. No requiere instalar ni levantar un servidor de BD aparte ni drivers extra (`psycopg2-binary`, etc.) — el archivo de BD vive dentro del propio repo, lo que facilita la prueba de portabilidad de este mismo criterio |
| Librería de variables de entorno | **`django-environ`** | Más documentada específicamente para Django y permite tipar valores (`bool`, listas) al leerlos |
| Paquete interno de Django | `config` (`django-admin startproject config .`) | Convención para separar el "paquete de configuración" del nombre del repo |
| Versión de Django | Fijada en `django<6` (rama 5.2 LTS) | Instalar sin restricción trae Django 6.1, que exige Python 3.12+; fijar la LTS evita que el proyecto se comporte distinto en un computador de laboratorio con Python más antiguo |

- [x] Crear el repo nuevo en GitHub, separado de la entrega anterior (`ev1`), con rama `main` protegida (exige Pull Request) desde **antes** del primer commit de código
- [x] Crear `.gitignore` (excluye `.env`, `.venv/`, `__pycache__/`, `db.sqlite3`) **antes** de generar el entorno virtual o el proyecto — evita que un `git add .` temprano suba algo sensible por accidente
- [x] Crear una rama de trabajo (`feature/fase1-entorno-bd`) para todo el setup, ya que `main` quedó protegida y no admite commits directos — adelanta el flujo de Git que exige la Fase 8
- [x] Crear entorno virtual e instalar Django (`pip install "django<6"`)
- [x] Crear el proyecto Django (paquete `config`)
- [x] Instalar `django-environ`
- [x] Crear `.env` local (no se sube) y `.env.example` (sí se sube, mismos nombres de variable sin valores reales): `SECRET_KEY`, `DEBUG`, `DB_ENGINE`, `DB_NAME`
- [x] Configurar `DATABASES` en `settings.py` leyendo `ENGINE` y `NAME` desde variables de entorno — nunca hardcodeadas. Con SQLite no hay host/puerto/usuario/password que externalizar (no es un motor cliente-servidor): lo que se lee desde `.env` es el **nombre del archivo** de BD (`DB_NAME`), combinado con `BASE_DIR` después de leerlo como string y no como `Path` por defecto, para que el resultado sea un `Path` válido tanto si `DB_NAME` viene de `.env` como si cae al valor por defecto
- [x] Generar `requirements.txt` con `pip freeze` desde el inicio (y repetirlo cada vez que se agregue un paquete nuevo en fases siguientes, no solo al final)
- [x] Correr `python manage.py check` sin errores
- [x] Migrar por primera vez en local (`python manage.py migrate`) — crea `db.sqlite3` con las tablas de `auth`, `admin`, `sessions`, etc.
- [x] Commit, push de la rama, Pull Request y merge a `main`
- [x] Probar que migra sin errores en un entorno limpio: clonar el repo en una carpeta nueva, venv nuevo, `pip install -r requirements.txt`, copiar `.env.example` a `.env` y completar `SECRET_KEY`, `check` + `migrate` — confirma portabilidad real, no solo "en mi compu funciona"
- [x] Documentar en el README los pasos exactos: clonar → crear venv → instalar requirements → copiar `.env.example` a `.env` y completar → migrar → levantar el servidor

**Punto de verificación:** cualquiera del equipo debe poder explicar de memoria cómo se leen las
variables de entorno en `settings.py` (Edición 1 a 3 del Paso 8 de la guía detallada), sin mirar el
código — la pregunta dirigida es sobre el proyecto entregado, no sobre definiciones memorizadas. Vale
la pena que las 4 personas lean al menos ese paso, aunque no lo hayan escrito ellas mismas.

---

## Fase 2 — Modelo de datos y migraciones

**Bloqueante — lo más importante de la fundación técnica.** Debería discutirse entre varios, no
decidirlo una sola persona en aislamiento, porque todos los bloques siguientes dependen de estos
nombres de campos y relaciones.

Las entidades completas están en el documento SGR (§8/§12); acá se seleccionan las necesarias para el
enunciado de Django Admin. El alcance quedó cerrado en **4 maestras + 3 operativas** (7 entidades en
total, ver Fase 0) — se agregó `Validación` como 3ª operativa respecto al recorte original de 6 — dejando
fuera del recorte el resto del MVP completo que no hace falta para esta evaluación puntual
(Compromiso/agenda colectiva, Indicador con semáforo, Auditoría automática — buenas de agregar si sobra
tiempo, no imprescindibles).

- [x] **Tablas maestras (usar 4 de estas):**
  - **Delegación** — identificador, nombre, estado, responsable, ámbito (RF-001). Es la entidad que scopea todo el sistema.
  - **Funcionario** — PK propia `idInstitucional`, nombre, cargo (FK), delegación (FK), estado (RF-002). Se relaciona con `auth.User` vía `OneToOneField` **directa** (sin modelo `Perfil` intermedio) para poder loguearse con el admin nativo. Los roles múltiples (Administrador, Delegado, Funcionario, Verificador) se gestionan con `auth.Group`, no como campo `rol` propio — se descartó heredar de `AbstractUser` por menor flexibilidad a futuro y porque `AUTH_USER_MODEL` no se puede cambiar después de la primera migración con datos.
  - **Cargo** — nombre del cargo, ítems medibles asociados, vigencia (RF-003).
  - **Período** — fecha inicio, fecha término, estado, días computables (RF-005). Trae una regla de negocio lista para usar como validación en Fase 5: la fecha de término no puede ser anterior al inicio.
  - *(Opcional, 5ta maestra)* **Ítem/Meta** — ítem, valor objetivo, unidad, ponderador (RF-006, RF-007). → descartada, ver Decisión 11/"Fuera de alcance" en `decisiones.md`.

  → **Confirmado implementado** en `core/models.py`: las 4 maestras existen tal cual, con `Delegacion.id` y `Funcionario.id_institucional` como PK natural string (Decisión 11).
- [x] **Tablas operativas (las 3 confirmadas):**
  - **Actividad** — fecha, solicitud/problema, acción, contacto, teléfono, ítem, autor (FK a Funcionario), **período** (FK obligatoria a Período — habilita `list_filter` por período en Fase 4 y la validación de Fase 5), **tipo/servicio/atención/subatención** (`CharField` de texto libre, **sin** `choices` fijos: el catálogo de estos 4 campos es abierto/administrable, no cerrado tipo ENUM; solo 2 de los 4 tienen catálogo cerrado real en la fuente original, así que texto libre es consistente para los 4), estado. Entidad principal del flujo operativo. *(RF-011 pide generar un código único para nombrar/vincular la evidencia — se cubre con la FK real `Evidencia.actividad` + el propio `Evidencia.codigo`, no con un campo aparte en `Actividad`; ver Decisión 3 de `decisiones.md`.)*
  - **Evidencia** — código (identificador único e inmutable, RF-011), archivo o vínculo, actividad (FK), autor, fecha, estado de revisión (RF-012, RF-013). Candidata natural para el Inline de Fase 5 (una Actividad se edita junto con su Evidencia).
  - **Validación** *(nueva respecto al recorte original de 6 entidades)* — relación 1:0..1 hacia Evidencia; campos `decision`, `fecha`, `observacion`, `resultado`, `version`, `funcionario` (verificador, FK). Se implementa como entidad propia y no como campo simple `revisado_por` en Evidencia, porque el diagrama de dominio completo de Actividad 3 ya la modelaba así — usar el campo simple ahora habría significado migrar datos a una tabla nueva en la próxima entrega. Habilita un segundo Inline (`ValidacionInline` en `EvidenciaAdmin`) casi gratis para Fase 5.

  → **Confirmado implementado** en `core/models.py`: `Actividad.periodo` es FK obligatoria (Decisión 1), `Evidencia.archivo` es `FileField` real (Decisión 7), `Validacion.evidencia` es `OneToOneField` FK+UK (Decisión 3). Campo `codigoVerificador` correctamente ausente (retirado por Decisión 3).
- [x] Confirmar el campo crítico de scoping (Fase 6): `Funcionario.delegacion` (FK) y, por extensión, `Actividad.autor.delegacion`, `Evidencia.actividad.autor.delegacion` y `Validacion.evidencia.actividad.autor.delegacion` — un funcionario de la Delegación X no debe ver ni modificar Actividades (ni su Evidencia/Validación asociada) cuyo autor pertenece a la Delegación Y (esto es CA-07 del documento SGR). → confirmado: `Funcionario.delegacion` existe como FK `PROTECT` (Decisión 8); la cadena de scoping queda lista para Fase 6, incluido el caso borde del Administrador sin `Funcionario` documentado en Decisión 6.
- [x] Armar/ajustar el diagrama ER con tipos de datos y relaciones — esto se reusa directo en el Informe (Fase 7), hacerlo ahora ahorra tiempo después. Relaciones: Delegación 1→N Funcionario, Funcionario N→1 Cargo, Funcionario 1→N Actividad, Período 1→N Actividad (FK obligatoria), Actividad 1→1 (o 1→N) Evidencia, Evidencia 1→0..1 Validación, Período independiente o relacionado a Meta si se agrega esa 5ta maestra → confirmado: `docs/assets/mer_evaluacion_2_django_admin.puml` + `.png`, enlazados desde el README.
- [x] Crear los modelos en Django con sus tipos de datos y relaciones (`ForeignKey`, `on_delete`, `related_name`), incluida la FK `Actividad → Período` y la relación 1:0..1 `Evidencia → Validación` → confirmado: los 8 FK/O2O de `core/models.py` coinciden exactamente con la tabla de la Decisión 10.
- [x] Agregar el `OneToOneField` de `Funcionario` hacia `auth.User` (no crear un modelo `Perfil` aparte) → confirmado: `Funcionario.user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='funcionario')`.
- [x] Crear los `auth.Group` para los roles (Administrador, Delegado, Funcionario, Verificador) — los roles se gestionan por grupo, no por un campo `rol` en el modelo → confirmado en el Admin durante la verificación de Fase 3: los 4 grupos existen.
- [x] Generar y aplicar migraciones (`makemigrations`, `migrate`) → confirmado: corridas sin errores.
- [x] Registrar todo en el admin sin personalizar aún, solo para confirmar que migró bien y las relaciones se ven correctas → confirmado: `core/admin.py` con `admin.site.register()` simple para las 7 entidades.

**Punto de verificación:** alguien del equipo (cualquiera, por la regla de pregunta dirigida) debe poder
explicar por qué se eligió cada tabla maestra/operativa y qué representa cada relación, sin mirar el
código. Esto incluye poder justificar por qué `Validación` es una entidad separada y no un campo simple
dentro de `Evidencia`, y por qué los roles van en `auth.Group` y no en un campo propio de `Funcionario`.
→ **Aún por ensayar en voz alta entre los 4** — el contenido para responderlo ya está completo en
`docs/decisiones.md` (Decisiones 1 a 11), pero el ensayo en sí queda para la preparación de Fase 9.

---

## Fase 3 — Datos de prueba reproducibles (carga obligatoria)

**Bloqueante, segunda.** Si se hace mal o tarde, tira a 0 varios criterios grandes (Admin Pro,
Seguridad, Revisión en vivo) porque el enunciado exige mecanismo *reproducible*, no datos cargados a
mano una vez.

- [x] Elegir mecanismo: fixture JSON + `loaddata`, o management command propio (ej. `seed_sgr` / `seed_data`) → resuelto: management command (`core/management/commands/seed_sgr.py`)
- [x] Crear los `auth.Group` de roles (Administrador, Delegado, Funcionario, Verificador) como parte del seed, antes de crear usuarios → confirmado en el Admin: los 4 grupos existen y se crean antes de los usuarios en `handle()`
- [x] Crear **al menos 2 Delegaciones** distintas con nombres ficticios (el documento SGR §2.1 prohíbe explícitamente usar datos reales de funcionarios o ciudadanos: "solo se utilizarán datos ficticios o anonimizados") → confirmado: `DEL-001` (Delegación Centro) y `DEL-002` (Delegación Norte)
- [x] Crear **al menos 2 usuarios de prueba** con roles distintos, cada uno en una Delegación distinta, con su `Funcionario` enlazado 1:1 a su `auth.User` y asignado al grupo correspondiente:
  - **Administrador** (superuser, permisos completos, grupo Administrador — "configura delegaciones, usuarios, cargos, catálogos, períodos, metas, ponderaciones y permisos") → confirmado: `admin_sgr`, con `Funcionario` propio `FUNC-ADMIN-001` (Decisión 6)
  - **Funcionario** (staff=True, is_superuser=False, acotado a su propia delegación, grupo Funcionario — "registra actividades, compromisos, avances, contactos, servicios y evidencias asociadas") → confirmado: `funcionario_demo`, `Funcionario` `FUNC-DEMO-001`, Delegación Norte
  - *(Opcional pero recomendado ahora)* **Verificador** (staff=True, grupo Verificador — es quien decide sobre `Validación` en Fases 5 y 6) → implementado también: `verificador_demo`, `Funcionario` `FUNC-VERIF-001`, Delegación Centro
- [x] Cargar al menos 1 **Período** con fechas válidas y asociar cada Actividad a su Período vía la FK obligatoria — sin Período asignado, `Actividad` no debería poder guardarse → confirmado: Período 2026-07-01 a 2026-12-31, ambas Actividades del seed lo referencian
- [x] Cargar Actividades y Evidencias para **ambas** delegaciones — sin esto no se puede demostrar el scoping en Fase 6 → confirmado: Actividad 1 (admin_funcionario, Delegación Centro) y Actividad 2 (funcionario_demo, Delegación Norte), cada una con su Evidencia
- [x] Cargar al menos 1 registro de **Validación** sobre una Evidencia existente, para poder demostrar el `ValidacionInline` en Fase 5 → confirmado: Validación 1 sobre `EVID-001`, `funcionario` = Verificador Demo Centro
- [x] Usar valores ya normalizados (misma capitalización, sin variantes) en los 4 campos de texto libre de Actividad (tipo, servicio, atención, subatención) — al no tener `choices`, cualquier variante de escritura aparece como opción distinta en el `list_filter` del Admin y ensucia la demo → confirmado visualmente en el Admin: "Primera Atención" / "Atención Presencial" / "Informes Sociales" / "Informe Aporte Económico", tal como fija la Decisión 4
- [x] Documentar las credenciales de estas cuentas de prueba en el README (nunca usar credenciales personales — lo prohíbe el enunciado, y el documento SGR lo refuerza en §15.3: "no existen contraseñas ni datos reales en el repositorio, base o capturas") → confirmado: sección "Cuentas de prueba" en `README.md` con las 3 cuentas ficticias generadas por `seed_sgr`
- [x] Probar la carga completa desde una base vacía (borrar BD, migrar, correr el seed) al menos una vez antes de seguir — si falla acá, todo lo de abajo se construye sobre una base rota → confirmado: `db.sqlite3` borrado, `migrate` + `seed_sgr` corren limpio desde cero

**Punto de verificación:** correr `migrate` + el comando de seed en una máquina/entorno distinto y
confirmar que aparecen los usuarios y los datos de ambos contextos. → **Aún pendiente de probar en una
máquina/entorno realmente distinto** (todo lo anterior se probó en el mismo entorno de desarrollo,
incluido el reset desde base vacía) — dejar para el ensayo de Fase 9, o probarlo antes si el equipo
tiene acceso fácil a un segundo computador/venv.

---

## A partir de aquí: trabajo en paralelo (Fases 4, 5, 6, 7, 8)

Con el modelo (Fase 2) y los datos de prueba (Fase 3) cerrados, recién aquí conviene dividir por
persona según la tabla de reparto de la sección 0.

## Fase 4 — Admin Básico · *(10 pts)*

- [ ] Registrar las 4 maestras y las 3 operativas (Actividad, Evidencia, Validación) en `admin.py`
- [ ] Configurar `list_display` en cada una (columnas visibles en el listado)
- [ ] Configurar `search_fields` (campos buscables)
- [ ] Configurar `list_filter` en `Actividad` por delegación (vía autor), estado y **período** (ahora posible gracias a la FK de Fase 2) — evitar poner `list_filter` sobre los 4 campos de texto libre (tipo/servicio/atención/subatención) a menos que los datos de Fase 3 ya estén normalizados, o el filtro queda con opciones duplicadas
- [ ] Configurar `ordering` (orden por defecto)
- [ ] Configurar `list_select_related` donde el `list_display` muestre FK (incluye la nueva FK `Actividad.periodo`) — evita N+1 queries; es un detalle que el enunciado pide explícitamente y es fácil de olvidar
- [ ] Probar cada configuración con los datos cargados en Fase 3 — un `list_filter` sin datos variados no demuestra nada en la revisión en vivo

## Fase 5 — Admin Pro · *(22 pts, el que más vale)*

- [ ] **Inline (principal):** `Evidencia` como `TabularInline` o `StackedInline` dentro de `ActividadAdmin` — una Actividad se edita junto con su Evidencia asociada en la misma pantalla, justo el flujo que describe RF-012 ("la evidencia queda visible desde la actividad")
- [ ] **Inline (adicional, gracias a la 7ª entidad):** `ValidacionInline` dentro de `EvidenciaAdmin` — una Evidencia muestra su decisión de verificación (`decision`, `resultado`, `observacion`, `version`, verificador) en la misma pantalla. No reemplaza al Inline principal, lo refuerza: con los dos implementados el criterio queda cubierto con margen aunque uno tenga un detalle menor
- [ ] **Acción personalizada:** `@admin.action` sobre `Evidencia` para **aprobar o rechazar en lote** (cambia `estado_revision` a "Aprobada"/"Rechazada" sobre la selección) — corresponde directo a RF-013 ("un verificador autorizado deberá aprobar, rechazar o solicitar corrección de una evidencia")
- [ ] **Validación controlada (opción recomendada ahora):** `clean()` en el modelo `Actividad` para que su fecha esté dentro del rango del `Período` asignado — queda natural gracias a la FK `Actividad → Período` de Fase 2, y es justo la validación que motivó agregar esa FK. *Alternativas igual de válidas si prefieren repartir el trabajo distinto:* `clean()` en `Período` para que la fecha de término no sea anterior al inicio (RF-005), o no permitir guardar una Actividad sin código de evidencia cuando el estado es "Validada" (RF-011/RF-014). El enunciado pide explícitamente poder mostrar "un error controlado" en la demo — probar que el mensaje se ve bien en el admin, no solo que la validación "funciona en el backend"
- [ ] Probar los elementos implementados juntos con los datos de Fase 3 antes de dar por cerrada la fase (no solo revisar el código)

## Fase 6 — Seguridad y scoping por Delegación · *(15 pts)*

- [ ] Sobrescribir `get_queryset()` en los `ModelAdmin` de `Actividad`, `Evidencia` y `Validación` para que el Funcionario solo vea registros cuyo autor pertenece a su propia Delegación — la cadena es `Actividad.autor` / `Evidencia.actividad.autor` / `Validacion.evidencia.actividad.autor` (filtrando por `request.user`, ahora directo gracias al `OneToOneField` de Funcionario a User de Fase 2)
- [ ] Sobrescribir `has_change_permission()` / `has_delete_permission()` para impedir "modificar" registros de otra Delegación aunque se acceda por URL directa (`/admin/app/actividad/<id>/change/`)
- [ ] Restringir la acción sensible de Fase 5 a roles autorizados con `request.user.groups.filter(name=...)` (grupo Verificador), no un campo `rol` propio
- [ ] Restringir quién puede crear/editar `Validación` al grupo Verificador (`has_add_permission` / `has_change_permission`) — coherente con que es ese rol el que "aprueba, rechaza o solicita corrección"
- [ ] Verificar con los usuarios de prueba que: el Administrador ve TODAS las Delegaciones/Funcionarios/Actividades, y el Funcionario ve SOLO las de su propia Delegación (incluyendo su Evidencia y Validación asociada)
- [ ] Guardar capturas de esa prueba para el informe

**Nota:** esta fase depende 100% de que Fase 3 haya cargado datos de al menos 2 Delegaciones — si no,
no hay nada que demostrar y el criterio completo cae a 0 puntos según la regla del enunciado. Corresponde
exactamente a CA-07 del documento SGR.

## Fase 7 — Informe PDF · *(15 pts, trabajo continuo desde el día 1)*

**Quién:** todo el equipo, no una sola persona. Cada integrante documenta su propia fase a medida que
avanza (Maricel su Admin Pro, Constanza su Admin Básico, Valentina su Seguridad, Reinaldo su Setup +
Modelo + Seed); alguien del equipo compila todo en un solo PDF al final.

- [ ] Diagrama ER final con las 7 entidades y tipos de datos (debe coincidir con el código real, incluidas las FK `Actividad → Período` y `Evidencia → Validación`)
- [ ] Explicación breve de tablas maestras vs. operativas, incluyendo por qué `Validación` es una entidad propia y no un campo dentro de `Evidencia`
- [ ] Fragmento de `settings.py` mostrando `DATABASES` y uso de variables de entorno
- [ ] Capturas de los usuarios de prueba (incluido Verificador si se implementó) y la diferencia de acceso entre ellos
- [ ] Capturas del Admin (columnas, búsqueda, filtros, ordering)
- [ ] Captura de los dos Inline funcionando (Evidencia en Actividad, Validación en Evidencia), de la acción ejecutada y de la validación mostrando un error controlado
- [ ] Evidencia de scoping con datos de ambas delegaciones
- [ ] Instrucciones de cómo cargar los datos de prueba y levantar el proyecto
- [ ] Nombrar el PDF exactamente como pide el enunciado: `U2_Eval2_<NombreProyecto>_<Sección>.pdf`

## Fase 8 — Reproducibilidad y Git · *(9 pts, trabajo continuo desde el día 1)*

**Quién:** todo el equipo. Cada integrante trabaja en su propia rama (`feature/...`) y hace merge/PR de
su parte a medida que la termina; no es una tarea que se delega a una sola persona al final.

- [ ] `requirements.txt` actualizado
- [ ] README con instalación, entorno virtual, variables de entorno, migraciones, carga de datos y cuentas de prueba
- [ ] Confirmar que no hay `.env`, `.venv` ni datos sensibles en el repo
- [ ] Ramas por funcionalidad (`feature/admin-basico`, `feature/admin-pro`, `feature/seguridad`, etc.) + merge/PR hacia `main` — nada de commits directos
- [ ] Commits descriptivos durante todo el proceso, no solo al final
- [ ] Registrar el hash del commit final a evaluar

Esto es gratis si se hace bien desde el día 1, pero cuesta caro arreglarlo el último día.

---

## Fase 9 — Integración y ensayo de la revisión en vivo · *(20 pts, todos juntos)*

No es opcional ni se puede saltar — el enunciado pide explícitamente ensayar el flujo completo desde
un entorno limpio, y este ítem vale 20 pts por sí solo.

- [ ] Simular todo desde cero en otra carpeta/computador (o al menos un venv nuevo): clonar el repo, crear entorno, instalar dependencias, configurar `.env`, migrar, cargar el seed
- [ ] Ensayar el flujo exacto del enunciado: login admin → mostrar Admin completo → logout → login usuario limitado → restricciones → búsqueda/filtros/ambos Inline (Evidencia y Validación)/acción/validación (fecha de Actividad dentro del Período)/scoping
- [ ] Cronometrar el ensayo
- [ ] Definir quién del equipo puede explicar qué parte — el docente elige a quién le pregunta, no alcanza con que "el que lo programó" lo sepa; todos deben poder ubicar la implementación en el código y explicar su propósito (la pregunta dirigida descuenta 1 punto por criterio si la persona elegida no sabe explicarlo, y el descuento es al puntaje del **equipo**)
- [ ] Revisar que el repo no tenga `.env` ni `.venv` commiteados antes del hash final a entregar
- [ ] Confirmar el hash del último commit a evaluar y anotarlo junto con la URL del repo para el entregable