# Decisiones de diseño — Evaluación Sumativa II (Django Admin)

**Proyecto:** SGR — Sistema de Gestión de Resultados
**Caso:** Delegaciones municipales, Ilustre Municipalidad de La Serena
**Evaluación:** Backend (Programación Back End, TI3041) — distinta de la evaluación de Ingeniería de Software (repo `ev1`)
**Alcance de esta entrega:** 7 entidades (4 maestras: Delegación, Cargo, Funcionario, Período — 3 operativas: Actividad, Evidencia, Validación)

> Este documento registra únicamente las decisiones tomadas para esta entrega. El MER completo del dominio (14 entidades, `assets/actividad-3/clases-dominio.puml`) se mantiene como diseño de referencia para entregas futuras — ver sección "Fuera de alcance" al final.

---

## Decisiones tomadas

### Decisión 1 — Relación Actividad ↔ Período

**Decisión:** `Actividad` tiene una FK directa y obligatoria (`NOT NULL`) hacia `Periodo`.

**Justificación:**
- Habilita `list_filter` sobre una FK real en Admin Básico (`list_filter = ['periodo']`), sin lógica adicional.
- Permite la validación de Admin Pro (`clean()` del `ModelForm` de `Actividad`): la `fecha` de la actividad debe estar entre `periodo.inicio` y `periodo.termino`. Sin la FK no existe contra qué validar.
- Es coherente con el patrón ya usado en el dominio completo (`Periodo ||--o{ Meta`).
- Sin esta FK, `Periodo` queda desconectado de las demás 6 entidades del alcance de esta entrega.

**Alternativa descartada:** calcular el período vigente a partir de la fecha de la actividad, sin FK. Se descartó porque no habilita `list_filter` directo y elimina el caso de validación que la rúbrica pide demostrar.

---

### Decisión 1B — Motor de base de datos

**Decisión:** Se usa **SQLite** como motor de base de datos para esta entrega.

**Justificación:**
- Indicado explícitamente por el docente en clases (comunicación oral, no escrita en el enunciado ni en el plan de proyecto). Se documenta acá para que quede fijado por escrito y no vuelva a interpretarse como "el equipo puede proponer el motor" a partir de la Fase 1 (`Plan_Proyecto_SGR_Fusionado.md`, que no fija motor por asumir esa libertad).
- El enunciado solo exige que la conexión a la BD se configure mediante variables de entorno (`.env`) y que el proyecto migre en un entorno limpio — no exige un motor cliente-servidor en particular.
- SQLite no requiere instalar ni dejar corriendo un servicio de base de datos aparte, lo que simplifica el paso de portabilidad (clonar en limpio y migrar) que pide el criterio "Conexión BD + Migraciones".

**Alternativa descartada:** PostgreSQL. Era el supuesto inicial de la guía de Fase 1 generada antes de esta aclaración; se descarta porque contradice lo indicado por el docente en clases.

---

### Decisión 2 — Relación Funcionario ↔ sistema de login (`auth.User`)

**Decisión:** `Funcionario` mantiene modelo y PK propios (`idInstitucional`), y se relaciona con `auth.User` mediante `OneToOneField` (`user = models.OneToOneField(User, on_delete=models.CASCADE)`). Los roles múltiples (Administrador, Delegado, Funcionario, Verificador) se gestionan con `auth.Group`, no como atributo propio de `Funcionario`.

**Justificación:**
- Separa dos responsabilidades distintas: autenticación (`User`) y modelo de negocio (`Funcionario`). Cambian por razones distintas y no deberían acoplarse.
- Es el patrón estándar de la industria y el más documentado en Django — relevante con 4 personas de niveles distintos trabajando en paralelo.
- Mantiene flexibilidad para entregas futuras (más entidades, posibles tipos de cuenta que no sean `Funcionario`).
- `Funcionario.roles: ENUM[] multivaluado` (como aparece en el diagrama completo) no se implementa como atributo — se resuelve nativamente con `Group`, sin tablas nuevas.

**Alternativa descartada:** heredar de `AbstractUser` (`Funcionario(AbstractUser)`). Se descartó porque `AUTH_USER_MODEL` debe fijarse antes de la primera migración (sin vuelta atrás fácil una vez con datos), es menos flexible para entregas futuras, y es un patrón menos común si el equipo necesita buscar ayuda externa.

---

### Decisión 3 — Registro de la revisión de una Evidencia

**Decisión:** Se agrega `Validacion` como entidad propia (3ª operativa), con relación 1:0..1 hacia `Evidencia` (`evidencia` como FK+UK en `Validacion`). Campos: `decision`, `fecha`, `observacion`, `resultado`, `version`, y `funcionario` (verificador).

Se elimina el campo `codigoVerificador` de `Actividad` (presente en el diagrama completo). **Aclaración
de nombre:** pese al nombre, este campo no identifica a la persona que verifica — corresponde a RF-011
("generar un código único... para nombrar y vincular su evidencia"; confirmado también por el método
`generarCodigoVerificador()` del diagrama, que traduce el mismo requisito con otro nombre). Es decir, es
un código de **enlace** entre `Actividad` y su `Evidencia`, no un dato de la validación.

Se elimina porque queda redundante con la relación real `Evidencia → Actividad` (FK) y con el propio
`Evidencia.codigo`: al modelar la evidencia como entidad relacionada por FK, ya no hace falta que
`Actividad` genere y guarde un código aparte solo para nombrar/vincular su evidencia — el vínculo es la
relación de base de datos, y el identificador propio de esa evidencia es `Evidencia.codigo`. **No es
redundante con `Validacion`**, que registra la decisión de revisión (aprobar/rechazar/observación), no
el vínculo Actividad–Evidencia.

**Justificación (de crear `Validacion` como entidad propia):**
- Coincide con el diseño ya definido en el dominio completo (Actividad 3) — evita tener que migrar datos de un campo simple hacia una tabla nueva en la próxima entrega.
- Captura información que un campo simple (`revisado_por`) no puede: `observacion`, `resultado` explícito, `version` (para re-revisiones).
- Habilita un Inline adicional casi gratis (`ValidacionInline` en `EvidenciaAdmin`), reforzando el criterio de Admin Pro.
- 7 entidades sigue por sobre el mínimo pedido (4 maestras + 2 operativas) sin problema de rúbrica.

**Alternativa descartada:** campo `revisado_por` (FK nullable a `Funcionario`) directo en `Evidencia`. Se descartó por requerir migración de datos en la siguiente entrega y perder observación/resultado/versión.

---

### Decisión 4 — Campos de clasificación de Actividad (tipo, servicio, atención, subatención)

**Decisión:** Los 4 campos (`tipoActividad`, `servicio`, `atencion`, `subatencion`) se implementan como `CharField` de texto libre — **sin** `choices` fijos en el modelo Django.

**Justificación:**
- El equipo ya determinó, al diseñar el diagrama de clases en Actividad 3, que este catálogo es abierto/administrable — modelado como asociaciones a una clase genérica `ElementoCatalogo`, a diferencia de `EstadoCompromiso` y `Semaforo`, que sí son de conjunto cerrado y quedaron como `ENUM`. Usar `choices` (equivalente a un enum en Django) contradiría esa decisión de diseño ya tomada con el documento fuente completo delante.
- Verificado en la fuente (`fuentes/ppt-original.md`, Diapositiva 8): existe un catálogo cerrado real, pero **solo para 2 de los 4 campos y solo del área social** (`Tipo Atención`, `Sub Atención`). No hay catálogo cerrado para `Servicio` ni para el tipo de actividad general en ningún documento del caso.
- El riesgo de datos inconsistentes en el Admin (`list_filter` con valores duplicados por mayúsculas/espacios) se controla vía fixtures/seed normalizados, no vía restricción de esquema — coherente con que la carga de datos de prueba es responsabilidad del equipo.
- Deja el camino simple para migrar a FK real hacia `ElementoCatalogo` en una entrega futura.

**Alternativa descartada:** `CharField` con `choices` fijos. Se descartó por contradecir la decisión de diseño ya tomada en Actividad 3 sobre el carácter abierto del catálogo.

**Valores de ejemplo para fixtures de esta entrega:**

| Campo | Valores | Origen |
|---|---|---|
| Tipo Atención | Informes Sociales, Gestión de Subsidios, Derivación, Otras Gestiones Sociales, Entrega Emergencia, Otros | Citado directamente de `fuentes/ppt-original.md`, Diapositiva 8 |
| Sub Atención | Informe Aporte Económico, Informe Aporte Material, Informe Institución, Exención Pago Aseo Domiciliario, Orientación Social, IPS, PGU, SAP, SUF, Otros, Acta de Entrega | Citado directamente de `fuentes/ppt-original.md`, Diapositiva 8 |
| Servicio | Atención Presencial, Atención Telefónica, Gestión Interna, Orientación General | Definido por el equipo — no existe catálogo cerrado en la documentación del caso |
| Tipo Actividad | Primera Atención, Seguimiento, Cierre de Caso, Derivación Externa | Definido por el equipo — no existe catálogo cerrado en la documentación del caso |

---

### Decisión 5 — Usuarios de prueba para la demo

**Decisión:** 3 usuarios de prueba, cada uno en su `auth.Group` correspondiente:
- **Administrador** — superuser, permisos completos, grupo `Administrador`.
- **Funcionario** — staff, acotado a su propia `Delegación` vía `Funcionario.delegacion`, grupo `Funcionario`.
- **Verificador** — staff, puede crear/editar `Validacion`, grupo `Verificador`.

**Justificación:**
- El plan ya asumía la existencia de un rol Verificador en Fase 5 (Inline y restricción de `Validacion`) y Fase 6 (permisos sobre `Validacion`), así que agregar este usuario es coherencia con lo ya planificado, no una decisión nueva de fondo.
- Sin este usuario, esos ítems de Fase 5/6 quedarían sin nadie que los demuestre en vivo — el enunciado indica que una funcionalidad no demostrable por falta de datos/usuarios obtiene 0 puntos en el criterio.
- El costo de agregarlo es bajo: un usuario más en el seed, sin cambios estructurales.
- Permite demostrar dos dimensiones de seguridad en Fase 6 (por Delegación y por rol), no solo una.

**Alternativa descartada:** quedarse solo con el mínimo de 2 (Administrador + Funcionario). Se descartó porque deja sin demostración los ítems de `Validacion` ya presentes en el plan.

**Cómo se identifica el rol en código:** no es un campo/atributo en ningún modelo — es pertenencia a un `auth.Group`. Se consulta con `request.user.groups.filter(name="Verificador").exists()`.

---

### Decisión 6 — Criterio de seguridad (scoping + rol)

**Decisión:** El criterio de seguridad combina dos dimensiones, sin niveles intermedios adicionales:
1. **Scoping por Delegación:** Funcionario/Verificador solo ven y modifican registros de su propia Delegación (vía `Funcionario.delegacion` → `Actividad.autor` → `Evidencia`/`Validacion`).
2. **Restricción por rol:** solo el grupo `Verificador` puede crear/editar `Validacion`. `Administrador` no tiene restricción de ninguna de las dos dimensiones.

**Justificación:** corresponde a CA-07 del documento SGR y es la combinación que ya estaba escrita en la Fase 6 del plan de trabajo — se confirma tal cual sin agregar un nivel de permiso intermedio (ej. "Administrador de Delegación" con permisos parciales), para no ampliar el alcance de esta entrega.

**Caso borde resuelto — `User` sin `Funcionario` asociado:** dado que `Funcionario.user` es la FK (no al revés), un `auth.User` sin fila `Funcionario` es válido en el modelo y `request.user.funcionario` lanza `RelatedObjectDoesNotExist` en ese caso, no `None`. Se resuelve con dos capas, no una sola:
1. El seed de Fase 3 crea también una fila `Funcionario` para el superuser Administrador (coherente además con el dominio: quien administra el sistema es igualmente un funcionario institucional con delegación y cargo propios).
2. El código de `get_queryset()`/scoping en los `ModelAdmin` usa `hasattr(request.user, "funcionario")` antes de acceder al atributo, para tolerar cualquier `User` creado fuera del seed (ej. un `createsuperuser` manual durante debugging) sin romper el Admin en vivo.

Se descartó dejar solo una de las dos capas: solo el seed no cubre usuarios creados después; solo el `hasattr()` no resuelve el caso normal de demo, donde igual conviene que el Administrador tenga una identidad institucional completa.

---

### Decisión 7 — Tipo de campo para `Evidencia.archivoOVinculo`

**Decisión:** se implementa como `FileField` (subida real de archivo al servidor), no como `URLField` ni como `CharField` genérico.

**Justificación:**
- El caso de uso real (delegaciones subiendo fotos, PDFs de listas de asistencia, oficios como evidencia de una actividad) es una subida de archivo propio, no un enlace a un sistema externo ya existente.
- `FileField` es el campo nativo de Django para este propósito: gestiona almacenamiento (`MEDIA_ROOT`/`MEDIA_URL`), valida que el contenido sea un archivo real, y Django Admin entrega el widget de carga sin configuración adicional — coherente con que esta entrega es específicamente sobre Django Admin.
- Requiere configurar `MEDIA_ROOT`/`MEDIA_URL` en `settings.py` y servir archivos de media en desarrollo (`static()` en `urls.py`). Se documenta como paso explícito de Fase 2/3.

**Alternativa descartada:** `URLField` (asumiría que el archivo ya vive en un sistema externo como Drive/SharePoint, dependencia que el enunciado no pide) y `CharField` genérico (no valida nada, ambiguo entre ruta y URL). Si a futuro se necesita soportar también enlaces externos, se agrega un segundo campo opcional (`enlace_externo`) en vez de forzar un único campo ambiguo.

**Nombre de campo en `models.py`:** se simplifica a `archivo` (sin la partícula "OVinculo" del diagrama, que reflejaba una ambigüedad de diseño ya resuelta por esta decisión).

---

### Decisión 8 — Política general de `on_delete` en las FK

**Decisión:** `PROTECT` es la política por defecto para las FK del modelo, con dos excepciones puntuales a `CASCADE`:
1. `Funcionario.user` (`OneToOneField` a `auth.User`) → `CASCADE`, porque un `Funcionario` no tiene identidad propia sin su cuenta de usuario asociada; son la misma entidad partida en dos tablas.
2. `Validacion.evidencia` → `CASCADE`, porque una `Validacion` no tiene sentido de negocio propio sin la `Evidencia` que valida.

Todas las demás FK (`Funcionario.delegacion`, `Funcionario.cargo`, `Actividad.funcionario`, `Actividad.periodo`, `Evidencia.actividad`, `Validacion.funcionario`) usan `PROTECT`.

**Justificación:**
- El sistema existe para preservar rastro de gestión y rendición de cuentas — un borrado en cascada silencioso (ej. borrar un `Periodo` y arrastrar sus Actividades, Evidencias y Validaciones ya aprobadas) destruye historial que el sistema debe conservar.
- El propio diseño ya señala esta intención: casi todas las entidades del diagrama tienen un campo `estado` (BOOLEAN), lo que indica que el patrón esperado es desactivar/archivar registros, no borrarlos físicamente.
- `PROTECT` obliga a una decisión consciente: si alguien intenta borrar un `Funcionario` con Actividades registradas, Django lanza `ProtectedError` en vez de arrastrar todo en cadena.

**Alternativa descartada:** `CASCADE` como default general. Se descartó por el riesgo de pérdida de historial en un sistema de auditoría/rendición de cuentas; se reserva solo para los dos casos donde el hijo no tiene identidad propia sin el padre.

---

### Decisión 9 — Acción personalizada de Admin Pro

**Decisión:** la acción personalizada del criterio "Admin Pro" es **aprobar evidencias en lote**: sobre `EvidenciaAdmin`, una acción que toma las Evidencias seleccionadas y crea/actualiza su `Validacion` asociada con `resultado=True`, `funcionario` = usuario verificador actual y `fecha` = hoy.

**Origen de esta decisión:** se evaluó puntualmente en conversación con asistencia de IA, no en una sesión de equipo aparte — se deja constancia explícita para que la trazabilidad sea consistente si se pregunta en la defensa cuándo y por qué se descartó la alternativa.

**Justificación:**
- El rol `Verificador` (Decisión 5/6) ya existe específicamente para revisar evidencias una por una; esta acción es la extensión natural de ese trabajo hecho en lote, con ahorro de tiempo real y no una función decorativa solo para cumplir el criterio.
- Usa exclusivamente entidades y relaciones ya definidas (`Evidencia`, `Validacion`, `Funcionario`) sin abrir preguntas de negocio nuevas.
- Refuerza en la demo la Decisión 3 (Validación como entidad propia): sin esta acción, aprobar evidencia por evidencia vía Django Admin normal sería tedioso — la acción en lote es lo que le da sentido práctico a esa decisión de diseño.
- Sirve también para demostrar en vivo el criterio de seguridad (Decisión 6): la acción solo debe estar disponible/ejecutable para el grupo `Verificador`.

**Alternativa descartada:** cerrar actividades de un período (marcar `Actividad.estado` de todas las actividades de un `Periodo` como cerradas). Se descartó porque obliga a definir qué pasa con actividades sin evidencia o sin validación completa al momento del cierre — reglas de negocio no resueltas en este documento — mientras que aprobar evidencias en lote no requiere resolver nada adicional.

**Comportamiento frente a Evidencias que ya tienen `Validacion` — decidido explícitamente, no dejado a la implementación:** dado que `Validacion.evidencia` es FK+UK (relación 1:0..1, Decisión 3), la acción **no** hace `update_or_create` sobre una `Validacion` existente — eso pisaría un resultado previo (ej. un rechazo) sin dejar rastro, contradiciendo la razón de ser del campo `version` y de `Validacion` como entidad separada con historial. En su lugar, la acción:
1. Excluye del procesamiento cualquier `Evidencia` que ya tenga `Validacion` asociada, y lo reporta en el mensaje de resultado (ej. "3 evidencias validadas, 2 omitidas por ya tener validación").
2. Excluye también cualquier `Evidencia` sin `archivo` cargado, y lo reporta igual.
3. Solo crea `Validacion` nueva para las Evidencias restantes (sin `Validacion` previa y con `archivo` presente).

Se descartó permitir re-aprobar generando una segunda fila de `Validacion` por versión, porque el UK actual sobre `evidencia` no lo permite sin romper el 1:0..1 confirmado en ambos `.puml` — cambiar ese UK está fuera del alcance de esta decisión.

---

### Decisión 10 — `related_name` de cada FK

**Decisión:** se fija la siguiente convención para todas las FK del modelo (acceso inverso desde el modelo padre):

| FK | Modelo destino | `related_name` | Acceso inverso |
|---|---|---|---|
| `Funcionario.user` | `auth.User` | `funcionario` | `user.funcionario` (singular, `OneToOneField`) |
| `Funcionario.delegacion` | `Delegacion` | `funcionarios` | `delegacion.funcionarios.all()` |
| `Funcionario.cargo` | `Cargo` | `funcionarios` | `cargo.funcionarios.all()` |
| `Actividad.funcionario` | `Funcionario` | `actividades` | `funcionario.actividades.all()` |
| `Actividad.periodo` | `Periodo` | `actividades` | `periodo.actividades.all()` |
| `Evidencia.actividad` | `Actividad` | `evidencias` | `actividad.evidencias.all()` |
| `Validacion.evidencia` | `Evidencia` | `validacion` | `evidencia.validacion` (singular, relación 1:0..1 — Decisión 3) |
| `Validacion.funcionario` | `Funcionario` | `validaciones_realizadas` | `funcionario.validaciones_realizadas.all()` |

**Justificación:**
- Plural para relaciones 1:N (`funcionarios`, `actividades`, `evidencias`), singular para relaciones 1:1 (`funcionario`, `validacion`) — convención estándar de Django, predecible para cualquiera que lea el código sin tener que revisar `models.py`.
- `Validacion.funcionario` usa `validaciones_realizadas` en vez de `validaciones` a secas para distinguirlo explícitamente del rol: dentro de `Funcionario` ya existe el acceso inverso `actividades` (lo que el funcionario *registra* como autor) y se necesita un nombre distinto para lo que el funcionario *valida* como verificador — evita ambigüedad al leer `funcionario.validaciones_realizadas.all()` en el código de permisos/scoping (Decisión 6).

**Por qué no todas las relaciones de `Funcionario` siguen el mismo patrón de nombre corto (pregunta esperable en la defensa):** en `Actividad`, `Funcionario` aparece en un solo rol (autor), así que `actividades` no es ambiguo. En `Validacion`, `Funcionario` aparece semánticamente como verificador, y el nombre corto ya está tomado por el otro rol — de ahí el nombre más largo y explícito en ese caso puntual. No es inconsistencia de estilo: es desambiguación donde el mismo modelo cumple dos roles distintos frente a `Funcionario`.

**Nota de implementación ligada a `Funcionario.user` → `related_name="funcionario"`:** como es un `OneToOneField`, el acceso es `request.user.funcionario` (sin `.all()` ni `.first()`). Ver el caso borde de `User` sin `Funcionario` asociado (ej. superusers) documentado en la Decisión 6.

---

### Decisión 11 — PK natural (string) en `Delegacion`, `Funcionario` y `Evidencia`

**Decisión:** estos tres modelos usan una clave primaria natural de tipo `CharField`, en vez del `id` autoincremental que Django agrega por defecto:
- `Delegacion.id` — identificador de delegación ya asignado por la Municipalidad.
- `Funcionario.id_institucional` — identificador institucional del funcionario, ya existente fuera del sistema.
- `Evidencia.codigo` — identificador único e inmutable exigido por RF-011, generado o registrado al crear la evidencia.

**Justificación:** las tres son casos de identificadores de negocio que ya existen de forma independiente al sistema (vienen de otro proceso o convención municipal), no un correlativo que a Django le corresponda inventar. Usar el `id` autoincremental por defecto en estos tres casos escondería el identificador real detrás de un número interno sin significado, obligando a mantener ambos (el autoincremental y el de negocio) en vez de uno solo. Esto ya estaba fijado en el diseño de origen — ambos diagramas ER (`docs/assets/mer_general_mvp.puml` y `docs/assets/mer_evaluacion_2_django_admin.puml`) marcan explícitamente estos tres campos como `«PK»` de tipo `VARCHAR`; esta decisión solo deja registrado el porqué para la defensa, no cambia el diseño.

**Resto de modelos (`Cargo`, `Periodo`, `Actividad`, `Validacion`):** usan el `id` autoincremental por defecto de Django, porque no tienen un identificador de negocio preexistente que reemplazarlo — son registros que el propio sistema origina.

**Alternativa descartada:** usar `id` autoincremental en los 7 modelos y agregar el identificador de negocio como un campo `unique=True` aparte. Se descartó por duplicar el concepto de identificador sin necesidad, cuando el de negocio ya cumple los requisitos de una PK (único, estable, no nulo).

---

## Verificación de alcance contra la rúbrica

Las 7 entidades escogidas (Delegación, Cargo, Funcionario, Período, Actividad, Evidencia, Validación) fueron confirmadas como necesarias y suficientes para cada criterio de esta evaluación:

| Criterio | Cómo se cubre |
|---|---|
| Admin Básico (4 maestras + 2 operativas) | 4 maestras + 3 operativas (por sobre el mínimo) |
| Inline | `ValidacionInline` en `EvidenciaAdmin` |
| Acción personalizada | Aprobar evidencias en lote, restringida al grupo `Verificador` (Decisión 9) |
| Validación (`clean()`) | Fecha de `Actividad` dentro del rango de su `Periodo` |
| Seguridad / scoping | Vía `Funcionario.delegacion_id` → filtra `Actividad` y `Evidencia` por delegación del usuario logueado |

No se agregan entidades adicionales solo para "tener más" — cada una de las 7 tiene una función verificable en la rúbrica.

---

## Fuera de alcance para esta entrega (planificado para entregas futuras)

Las siguientes entidades del dominio completo (Actividad 3, 14 entidades) **no se implementan en esta evaluación**, por decisión de fasificación del proyecto — no por olvido:

- `Funcion`
- `CargoFuncion` (tabla puente Cargo↔Función)
- `Meta`
- `ElementoCatalogo` (los 4 campos de clasificación de Actividad son texto libre por ahora — ver Decisión 4)
- `Compromiso`
- `Indicador`
- `Auditoria`

El MER completo (14 entidades) se adjunta como anexo en el informe, documentando que esta entrega implementa un subconjunto de 7 entidades sobre ese diseño de dominio ya definido.

## Pendientes

- [x] ~~Definir la acción personalizada concreta de Admin Pro~~ → resuelto: aprobar evidencias en lote, restringida al grupo `Verificador` (Decisión 9).
- [ ] Confirmar reparto de las **fases del plan de trabajo** entre los 4 integrantes del equipo (pendiente fuera de esta conversación — no bloquea el inicio de Fase 1).
- [ ] Revisar si, al incorporar `ElementoCatalogo` en una entrega futura, migrar los 4 campos de texto libre de `Actividad` hacia FK reales.
- [x] ~~Confirmar si `Meta`/`CargoFuncion` se incorporan en esta entrega~~ → resuelto: quedan fuera de alcance, se mantienen las 7 entidades del diagrama actual. `Cargo` conserva una sola relación activa (`Cargo → Funcionario`) por ahora.
- [x] ~~Afinar tipos de datos definitivos de cada campo (`IntegerField` vs `PositiveIntegerField`, `FileField` vs `URLField`, etc.)~~ → `Evidencia.archivoOVinculo` resuelto como `FileField` (Decisión 7). Resto de tipos numéricos (`PositiveIntegerField` vs `IntegerField`) queda para revisión campo a campo al momento de escribir `models.py`.
- [x] ~~Definir política de `on_delete` en las FK~~ → resuelto: `PROTECT` por defecto, `CASCADE` solo en `Funcionario.user` y `Validacion.evidencia` (Decisión 8).
- [ ] **Nuevo, para Fase 3 (seed):** el default `PROTECT` (Decisión 8) implica que el orden de borrado/recreación de fixtures importa, y que un comando de seed no idempotente puede trabarse contra sus propias protecciones al re-ejecutarse sobre datos parcialmente cargados. Resolver con una de estas dos vías al construir el seed: (a) usar `get_or_create` en el management command, o (b) documentar en el README que el único método soportado de reset es borrar `db.sqlite3` y volver a migrar — nunca borrar registros sueltos desde el Admin. Verificar además que `PRAGMA foreign_keys=ON` esté activo en la conexión SQLite (por defecto lo está desde Django 3.x, pero conviene confirmarlo en la demo, no asumirlo).
- [ ] **Nuevo, para Fase 2 (settings/config):** configurar `MEDIA_URL` y `MEDIA_ROOT` en `settings.py`, y servir archivos de media en `urls.py` en desarrollo (`static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)`). Sin esto, el `FileField` de la Decisión 7 guarda la ruta en la base de datos pero no tiene dónde escribir ni cómo servir el archivo físico — la subida y el link "ver archivo" del widget de Admin fallarían en la demo. Confirmado ausente en el `settings.py` actual del repo; es el ítem de mayor impacto práctico pendiente antes de la revisión en vivo.
- [x] ~~Definir `related_name` de cada FK~~ → resuelto: convención plural/singular según cardinalidad, ver Decisión 10.
