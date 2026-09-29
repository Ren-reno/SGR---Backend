# Decisiones de diseño — Evaluación Sumativa II (Django Admin)

**Proyecto:** SGR — Sistema de Gestión de Resultados
**Caso:** Delegaciones municipales, Ilustre Municipalidad de La Serena
**Evaluación:** Backend (Programación Back End, TI3041) — distinta de la evaluación de Ingeniería de Software (repo `ev1`)
**Alcance de esta entrega (evaluación formativa en curso, criterios 2.1.1–2.1.4 de `docs/Evaluacion_Formativa_U2_BackEnd_TI3V41_INACAP.md`):** 10 entidades — 6 maestras (Delegación, Cargo, Período, Meta, ElementoCatalogo, Compromiso) y 4 operativas (Funcionario, Actividad, Evidencia, Validación).

> Este documento registra las decisiones tomadas para las distintas entregas que comparten este repo. El MER completo del dominio (14 entidades, `assets/actividad-3/clases-dominio.puml`) fue fijado por la Decisión 14 como alcance futuro, pero la Decisión 15 aclara que ese alcance de 8 módulos/14 entidades corresponde a la Evaluación Sumativa III (Eva 3, aún no entregada) — no a la evaluación formativa que se está desarrollando ahora mismo, documentada en `docs/Evaluacion_Formativa_U2_BackEnd_TI3V41_INACAP.md`. Ver Decisión 15 y sección "Alcance de entidades" al final para el detalle de qué corresponde a cada entrega.

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

### Decisión 9-bis — `estado_revision` al aprobar en lote

**Decisión:** además de crear la `Validacion` nueva, la acción "aprobar evidencias en lote" (Decisión 9) marca `Evidencia.estado_revision = 'Aprobada'` en las Evidencias que efectivamente procesa — y solo en esas.

**Origen de esta decisión:** se definió durante la construcción de Fase 5, igual que la Decisión 9, y quedó marcada como "pendiente de registrar formalmente" en `Fase5_Admin_Pro_Guia.md` hasta esta actualización (agregada en la revisión cruzada de Fase 4/5/6).

**Justificación:**
- `Evidencia.estado_revision` (RF-012/RF-013) necesita reflejar el resultado de la revisión en algún punto del flujo; la Decisión 9 define la creación de `Validacion` pero no toca explícitamente este campo, dejando un vacío entre "existe una Validación aprobada" y "la Evidencia se ve aprobada en su propio listado".
- Actualizarlo dentro de la misma acción (y no en un flujo aparte) mantiene en un solo lugar del código toda la lógica de qué significa "aprobar una evidencia en lote", en vez de repartir el efecto en dos sitios distintos del Admin.

**Criterios exactos aplicados (para que el código y esta decisión no diverjan):**
1. Se actualiza **solo** en las Evidencias que reciben `Validacion` nueva en esa misma ejecución de la acción.
2. Las Evidencias excluidas del procesamiento (ya tenían `Validacion`, o no tienen `archivo` cargado) **no** tocan `estado_revision` bajo ningún motivo — no hay decisión, ni en la 9 ni en esta 9-bis, sobre qué hacer con esos dos casos, así que no se inventa una regla para ellos.
3. Este es el único punto del código donde `estado_revision` cambia; no se modifica en ningún otro flujo del Admin.

**Alternativa descartada:** dejar `estado_revision` sin tocar y actualizarlo a mano aparte. Se descartó porque duplicaría el trabajo manual que la acción en lote ya existe para evitar.

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

### Decisión 12 — Borrado de `Validacion` desde el Admin

**Decisión:** nadie puede borrar una `Validacion` desde el Admin, ni siquiera `admin_sgr` (superuser / grupo Administrador). `ValidacionAdmin.has_delete_permission()` retorna `False` sin excepción.

**Origen de esta decisión:** detectada como hueco en la revisión cruzada de Fase 4/5/6 — la tabla de métodos nuevos de Fase 6 ya pedía `has_delete_permission()` en `ValidacionAdmin`, pero el código no lo tenía. No hay una decisión previa del equipo sobre este punto específico; se formaliza acá.

**Justificación:**
- Coherente con la Decisión 8 (`PROTECT` como política general de `on_delete`, justificada explícitamente para preservar rastro de gestión y rendición de cuentas).
- Coherente con la razón de ser de la Decisión 9: la acción de aprobar evidencias en lote usa `Validacion.objects.create()` y nunca `update_or_create()`, precisamente para no pisar una revisión previa sin dejar rastro. Permitir el borrado —aunque sea restringido por rol y Delegación— reabre el mismo problema por otra vía: el historial se pierde igual, ya sea por una actualización silenciosa o por un `DELETE`.
- Regla de una sola línea, sin casos borde adicionales que resolver (no hay que definir qué pasa si el Verificador que borra no es el mismo que creó la `Validacion`, ni qué pasa si esa `Validacion` ya fue citada en un reporte, etc.).

**Alternativa descartada:** permitir borrar solo al grupo Verificador/Administrador y solo dentro de su propia Delegación (mismo patrón de `has_change_permission`). Se descartó porque un Verificador podría borrar una revisión ya emitida, contradiciendo el espíritu "nunca perder el rastro" que ya motiva la Decisión 9 — el costo de habilitar el borrado no se justifica frente a un beneficio de negocio concreto que lo pida.

---

### Decisión 13 — Renombrado a inglés y separación en 3 apps (`accounts`, `organization`, `performance`)

**Origen de esta decisión:** la evaluación formativa recibida después de esta entrega (criterios 2.1.1–2.1.4, distinta y más amplia que el enunciado original de 2.1.1–2.1.2 contra el que se construyeron las Decisiones 1 a 12) exige explícitamente "nombres técnicos de modelos, tablas y campos en inglés" y "proyecto modular con mínimo 2 aplicaciones internas y responsabilidades separadas". Ninguna de las dos cosas estaba resuelta: las 7 entidades de esta entrega (Delegación, Cargo, Funcionario, Período, Actividad, Evidencia, Validación) estaban en español, y todas vivían en la única app `core`.

**Decisión:**
1. Se renombran las 7 entidades y sus campos a inglés: `Delegacion`→`Delegation`, `Cargo`→`Position`, `Funcionario`→`Employee`, `Periodo`→`Period`, `Actividad`→`Activity`, `Evidencia`→`Evidence`, `Validacion`→`Validation` (mapeo campo a campo documentado en el docstring de cada modelo). Los campos `estado` que eran `BooleanField` (activo/inactivo) pasan a `is_active`; los que eran `CharField` de texto libre (`Periodo.estado`, `Actividad.estado`) pasan a `status`, sin agregar `choices=` todavía — eso sigue pendiente (ver Pendientes).
2. Se reemplaza la app única `core` por 3 apps:
   - `accounts`: login, logout y recuperación de contraseña por código de 6 dígitos. Sin modelos propios de esta entrega — queda vacía y lista para esa pieza de trabajo, asignada aparte de los 8 módulos del dominio completo.
   - `organization`: `Delegation`, `Position`, `Employee`.
   - `performance`: `Period`, `Activity`, `Evidence`, `Validation`, y el comando `seed_sgr` (que depende de `organization.models`, no al revés).
3. Se ejecuta como reset limpio (borrar `db.sqlite3` y las migraciones de `core`, generar migraciones nuevas desde cero) en vez de `RenameModel`/`SeparateDatabaseAndState`, porque no hay datos reales que preservar — solo lo que genera `seed_sgr`, que es reproducible.

**Justificación:**
- 3 apps y no 2: meter el futuro modelo de recuperación de contraseña dentro de `organization` o `performance` solo para llegar al mínimo de 2 habría sido una costura artificial. El requisito pide "responsabilidades separadas", no un número exacto — `accounts` (acceso) es una responsabilidad genuinamente distinta a `organization` (estructura institucional) y a `performance` (el dominio de Gestión de Resultados), y se sostiene sola en la revisión oral.
- Dependencia en un solo sentido: `performance` importa de `organization` (`Employee` en `models.py` y `admin.py`), nunca al revés — se verificó que ningún archivo de `organization` necesita importar de `performance`. Es la misma razón por la que `seed_sgr` vive en `performance/management/commands/` y no en `organization/`.
- No se subdividió `performance` en apps más chicas para acercarse a un reparto más parejo de entidades: `Activity`↔`Evidence`↔`Validation` están fuertemente acopladas entre sí (inlines, scoping en cadena vía `evidence__activity__employee__delegation`), y separarlas solo agregaría FKs cruzadas sin ganar separación de responsabilidades real.
- Comentarios de diseño (Decisión 6, Bug 1, Bug 2, Decisión 9/9-bis) se mantienen en español y sin reescribir el razonamiento — solo se actualizan los nombres de clases/campos que mencionan, para que sean consistentes con el código real.

**Verificado antes de integrar esta decisión:** `manage.py check` sin errores; `makemigrations`/`migrate` limpios sobre base vacía; `seed_sgr` corre completo y es idempotente en una segunda corrida (incluye la asignación de permisos por grupo, que cambia de `("core", "view_actividad")` a `("performance", "view_activity")` — el `app_label` de los permisos de Django sigue el nombre de la app, no solo el del modelo); scoping por Delegación y la acción de aprobar evidencias en lote probados en runtime con los 3 usuarios de prueba, con el mismo resultado que antes del renombrado.

**Alternativa descartada:** mantener `core` y solo renombrar los modelos dentro de ella (resolvería el idioma pero no el mínimo de 2 apps), o partir en exactamente 2 apps forzando la recuperación de contraseña dentro de una de ellas (ver justificación arriba).

---

### Decisión 14 — Relación `Actividad.meta` y ampliación de alcance a 8 módulos / 14 entidades

**Origen de esta decisión:** el equipo define un alcance de proyecto distinto al fijado en este archivo hasta la Decisión 13: 8 módulos repartidos entre los 4 integrantes, construidos sobre las 14 entidades del diseño de dominio completo (Actividad 3) en vez de las 7 de esta entrega. Esta Decisión 14 dejaba pendiente su número exacto en la nota final de "Pendientes" de más abajo, que ya anticipaba que correspondería a 14 y no a 13 (ese número quedó tomado por la separación en apps).

**Decisión (confirmada por el docente, no un supuesto interno del equipo):** se agrega `Actividad.meta` como FK hacia `Meta`, `on_delete=PROTECT` (coherente con la Decisión 8). Una actividad aporta a una sola meta — no a varias, y no mediante coincidencia con los 4 campos de clasificación existentes (`activity_type`, `service`, `attention`, `sub_attention`), que siguen cumpliendo un rol distinto (clasificar la atención, no imputar avance).

**Justificación:** de tres opciones simuladas con datos de ejemplo (FK directa en `Actividad`; FK inversa desde `Meta` hacia un elemento de catálogo; tabla puente `ActividadMeta`), la FK directa es la única que no sobrecuenta el avance (RN-009) ni reescribe el resultado de períodos ya cerrados si el catálogo cambia después (RN-013, HU-25 criterio 2). Coincide además con la planilla real del cliente, donde cada actividad tiene una única columna ITEM.

**Alternativa descartada:** vincular por coincidencia con los 4 campos de clasificación existentes en vez de una FK directa. Se descartó porque una actividad podía coincidir con más de un clasificador y sumar de más a varias metas a la vez.

**Estado de implementación:** ninguna de las 7 entidades nuevas que requiere el alcance de 8 módulos (`ElementoCatalogo`, `Funcion`, `CargoFuncion`, `Meta`, `Compromiso`, `Indicador`, `Auditoria`) existe todavía en el repo a la fecha de esta anotación, y por lo tanto `Actividad.meta` tampoco — depende de que `Meta` exista primero. Esta decisión registra la regla de negocio confirmada; la sección "Alcance de entidades" más abajo deja de listar estas 7 entidades como excluidas de esta entrega.

**Lo que sigue explícitamente sin confirmar por el docente — no tratar como decisión cerrada:**
- Si `Indicador` se persiste como tabla o se calcula al vuelo. Hay una *recomendación* de tabla persistida, recalculada por un `services.py`, nunca editable a mano — pero el docente no lo ha zanjado.
- Si `Compromiso.delegacion` es una FK directa (fuente de verdad, validada con `clean()` contra la delegación del responsable) o si se infiere del responsable. Mismo caso: propuesta del equipo, sin confirmación docente.
- Si corresponde `created_at`/`updated_at`/`deleted_at` (borrado lógico) en todos los modelos.
- Si existe un mínimo de complejidad esperado por módulo.
- El estándar exacto de convención de nombres más allá de "inglés, consistente" — aunque en la práctica el código ya usa `snake_case` desde la Decisión 13.

**Pendiente de equipo:** el reparto de los 8 módulos entre los 4 integrantes.

---

### Decisión 15 — Separación de alcance: Evaluación Formativa (Eva 2 parte 2) vs. Evaluación Sumativa III (Eva 3)

**Origen de esta decisión:** al registrar la Decisión 14 se dejó escrito que las 14 entidades del dominio completo pasaban a ser "el alcance real de este repo". Eso generó una ambigüedad: ese alcance de 8 módulos corresponde en realidad a la Evaluación Sumativa III (Eva 3), evaluación distinta y **todavía no entregada** — no a la evaluación formativa que el equipo está desarrollando ahora mismo. Esta entrega formativa se agrega al repo como `docs/Evaluacion_Formativa_U2_BackEnd_TI3V41_INACAP.md` junto con esta misma decisión, y es la rúbrica vigente contra la que se mide el trabajo actual.

**Decisión:**
1. El alcance de 8 módulos / 14 entidades (Decisión 14) queda fijado como alcance de la **Eva 3**, no de la entrega en curso. La Decisión 14 no se revierte ni se borra — sigue vigente como registro de la regla de negocio de `Activity.meta` (FK, `on_delete=PROTECT`, una actividad aporta a una sola meta) y como planificación a futuro — pero deja de leerse como "lo que hay que tener construido ahora".
2. El alcance de la evaluación formativa en curso es el mínimo que exige `docs/Evaluacion_Formativa_U2_BackEnd_TI3V41_INACAP.md`: **mínimo 6 tablas maestras y 4 operacionales** (sin contar tablas internas de Django). Sobre las 7 entidades ya construidas (3 maestras: `Delegation`, `Position`, `Period` — 4 operativas: `Employee`, `Activity`, `Evidence`, `Validation`), se agregan 3 de las 7 candidatas que ya listaba la Decisión 14: `Meta`, `ElementoCatalogo` y `Compromiso`. Resultado: **6 maestras + 4 operativas = 10 entidades de negocio**, cumpliendo el mínimo exacto sin sobre-construir.
3. Las 4 entidades restantes de la Decisión 14 (`Funcion`, `CargoFuncion`, `Indicador`, `Auditoria`) quedan explícitamente fuera del alcance de esta entrega formativa — no por olvido, sino porque cada una tiene un motivo puntual documentado en la Decisión 14 misma: `Funcion`/`CargoFuncion` (tabla puente) dependen de una decisión de diseño que el equipo aún no toma (qué constituye una "función" en este dominio); `Indicador` tiene pendiente de confirmación docente si se persiste como tabla o se calcula al vuelo; y `Auditoria` exige trazabilidad campo a campo (valor anterior/nuevo) sobre todos los modelos vía señales — costo de implementación desproporcionado frente al puntaje que suma un ítem más de "6+4 tablas" en esta rúbrica puntual.

**Justificación:**
- Ambas evaluaciones (esta formativa 2.1.1–2.1.4, y la Eva 3 sumativa) comparten el mismo repositorio y el mismo `decisiones.md` — se sigue el mismo patrón ya usado entre la Evaluación Sumativa II (Decisiones 1–12) y esta formativa (Decisión 13): dejar registro escrito del cambio de alcance en vez de sobreescribir sin dejar rastro.
- `Meta`, `ElementoCatalogo` y `Compromiso` son, de las 7 candidatas de la Decisión 14, las que ya tienen requisito funcional redactado en la fuente del caso (`docs/Guia_Proyecto_Software_SGR_Alumnos.md`): RF-005 a RF-007 / HU-05 para `Meta`; RF-004 / HU-27 para `ElementoCatalogo`; RF-016 a RF-021 / HU-02, HU-12 a HU-15 para `Compromiso`. Ninguna de las tres abre una pregunta de diseño nueva sin resolver, a diferencia de las 4 que quedan fuera.
- `Meta` en particular ya estaba señalada por la propia Decisión 14 como bloqueador de `Activity.meta` ("Requerida antes de poder agregar `Activity.meta`") — construirla ahora no es alcance nuevo desconectado de lo ya decidido, sino completar una dependencia que ya estaba identificada por escrito.
- El estado de implementación es honesto en ambos sentidos: ninguna de las 7 candidatas de la Decisión 14 existía en el repo a esa fecha, y esta Decisión 15 no cambia eso — solo aclara cuáles 3 se construyen ahora y cuáles 4 quedan para la Eva 3.

**Alternativa descartada:** dejar el texto de la Decisión 14 tal cual (sin esta aclaración) y resolver el reparto de tablas solo de palabra entre el equipo. Se descartó porque la regla de defensa oral de esta rúbrica exige poder explicar cualquier implementación presentada como propia, y sin este registro escrito el alcance real de esta entrega quedaría ambiguo frente a una Decisión 14 que, leída sola, sugiere 14 entidades ya como alcance vigente.

---

### Decisión 16 — `CatalogItem`: solo `attention` migra a FK (Fase 2, paso 2.1)

**Origen:** el plan de la evaluación formativa deja abierta, antes de escribir `ElementoCatalogo`, si los 4 campos de texto libre de `Activity` (`activity_type`, `service`, `attention`, `sub_attention`) migran todos a FK ahora o quedan para Eva 3.

**Decisión:** `ElementoCatalogo` se implementa como `CatalogItem` (Decisión 13: inglés) y **solo `Activity.attention` migra** a FK (`on_delete=PROTECT`, Decisión 8, con `limit_choices_to` a la categoría `attention`). `activity_type`, `service` y `sub_attention` siguen como `CharField`, pendientes para Eva 3. La tabla es genérica: `category` distingue catálogos, así que sumar los otros 3 después no exige tablas nuevas.

**Justificación:**
- Es el cambio más invasivo del lote porque toca datos ya cargados por el seed; migrar los 4 de una vez multiplicaba ese riesgo por 4.
- Se eligió `attention` y no `sub_attention` por ser el campo padre de la relación Atención/Subatención de la Diapositiva 8 de la fuente del caso (Decisión 4). Migrar el padre primero deja la migración parcial más simple de completar.
- Coincide con la recomendación del propio plan de trabajo.

**Cómo se migró (3 migraciones, no una):** `0002` crea `CatalogItem` y un FK puente `attention_new` nullable; `0003` es una migración de datos que puebla el catálogo con los 6 valores de "Tipo Atención" de la Decisión 4 y asigna cada `Activity`; `0004` elimina el texto viejo y promueve el puente a `attention`. Un `AlterField` directo de `CharField` a `ForeignKey` no puede inferir a qué fila del catálogo corresponde cada texto, y en SQLite falla o corrompe la columna.

**Corrección posterior (patch 5): reversibilidad.** Como venía, `0004` no se podía revertir si existía al menos una `Activity` (`NOT NULL constraint failed: performance_activity.attention`, porque Django re-crea la columna de texto sin default), y el `reverse_populate` de `0003` era un `pass`, con lo que el texto original se perdía. Se agregó un `default=''` a la columna vieja antes de eliminarla y una reversa real que copia `CatalogItem.name` de vuelta a `attention`. Verificado: ida → vuelta a `0001` → ida, con datos reales, conservando el texto original.

**Limitación conocida:** `CATEGORY_CHOICES` solo tiene `attention`; las otras categorías se agregan en Eva 3.

---

### Decisión 17 — `Meta` y `Commitment`: reglas de negocio validadas y decisiones de diseño (Fase 2, pasos 2.2–2.4)

**`Meta` (paso 2.2)**
- Campos según el glosario de la Guía (sección 8: ítem, cargo, valor objetivo, unidad, ponderador) más `period`. FK a `Position` (no a `Employee`) porque RN-001 agrupa por cargo y período. `on_delete=PROTECT` (Decisión 8).
- `item_name` es texto libre, **no** FK a `CatalogItem`: la Decisión 14 descartó explícitamente vincular `Meta` a un elemento de catálogo porque sobrecuenta el avance (RN-009).
- **RN-002** (`target_value` > 0): validado en `clean()`.
- **RN-001** (suma de ponderadores de un cargo y período): `clean()` solo exige que **no supere 100%**, no que sea exactamente 100%. Un cargo carga sus metas una por una y suma menos de 100% mientras el conjunto está incompleto; la regla describe el conjunto completo, no cada alta parcial. El mecanismo de "excepción formalmente configurada" no está definido en ningún documento y queda pendiente.
- El nombre `Meta` coincide con la clase interna `class Meta:` de Django; no hay colisión real (verificado con `check` y `makemigrations`), pero conviene tenerlo presente al leer el código.

**`Activity.meta` (paso 2.3)**
- FK a `Meta`, `PROTECT`, **nullable**: una actividad puede registrarse sin imputar a ninguna meta todavía. Va en la misma rama que `Meta` para no dejarla sin relación con el resto del modelo. Implementa la regla ya confirmada por el docente en la Decisión 14.

**`Commitment` (paso 2.4)**
- **`delegation` como FK directa**, validada con `clean()` contra la delegación del responsable. Es la opción que sugería la Decisión 14; **sigue sin confirmar por el docente**. Se prefirió sobre inferirla porque, si se infiriera, reasignar el responsable (HU-15) cambiaría en silencio la delegación histórica de un compromiso ya reportado.
- **`status` con `choices`**: RF-018 fija las 4 transiciones exactas (Ingresado, Pendiente, En proceso, Realizado), así que es un conjunto cerrado y no un catálogo abierto (distinción que ya hacía la Decisión 4). Default `ingresado`.
- `territory` y `delegation` son campos distintos a propósito: HU-12 y el glosario los listan por separado.
- **Fuera de alcance:** RF-018 también pide historial de cambios de estado (estado anterior, nuevo, autor, fecha, observación). Es funcionalmente `Auditoria`, excluida por la Decisión 15. Se implementa el `status` simple sin historial.

**Registro en Admin (paso 2.5):** los tres modelos se registran con el patrón de `list_display`/`search_fields`/`list_filter`/`list_select_related` ya usado en `performance/admin.py`.

**Verificado (patch 5):** `Meta` rechaza `target_value` ≤ 0 y sumas > 100%, y al editar no se cuenta a sí misma; `Commitment` rechaza delegación distinta a la del responsable y `status` fuera de las 4 opciones.

---

### Decisión 18 — Quién gestiona `Commitment`, `Meta` y `CatalogItem` en el Admin (patch 5)

**Origen:** tras la Fase 2, `funcionario_demo` y `verificador_demo` recibían 403 en las tres entidades nuevas, porque `seed_sgr.py` no les daba permisos sobre ellas. Ningún paso del plan cubría ese reparto: el 2.5 solo pide registrarlas y el 5.1 solo extiende el scoping a las vistas web.

**Decisión:** el reparto sale de la tabla de actores de la Guía (sección 3), no de un supuesto del equipo.

| Rol | `Commitment` | `Meta` y `CatalogItem` |
|---|---|---|
| **Administrador** | ver, agregar, cambiar; ve todas las Delegaciones | control total (incluye borrar) |
| **Funcionario** | ver, agregar, cambiar, **solo de su Delegación** | sin acceso |
| **Verificador** | sin acceso | sin acceso |
| **Delegado** | sin permisos (ver más abajo) | sin acceso |

**Justificación:**
- La Guía asigna al Funcionario "registrar actividades, **compromisos**..." (HU-12 registrar, HU-13 actualizar estado) → permisos `view`/`add`/`change`.
- La Guía asigna al Administrador configurar "catálogos, metas y ponderaciones" → `Meta` y `CatalogItem` son configuración, no operación diaria. Que los demás reciban 403 ahí es lo que pide el documento, no un defecto.
- El Verificador "revisa evidencias, valida o rechaza": un compromiso no es una evidencia.

**Scoping obligatorio (no opcional):** dar permisos sin acotar por Delegación abría una fuga entre delegaciones. `CommitmentAdmin` filtra `get_queryset` por `delegation` (la propia del compromiso, no la de su responsable actual, por el mismo motivo de la Decisión 17), aplica `has_change_permission` por objeto, reutiliza el sentinel `_NO_EMPLOYEE` (Bug 2, Decisión 6) y limita los desplegables `delegation` y `responsible` a la Delegación del usuario.

**Sin borrado físico:** `Commitment` no se puede borrar desde el Admin, ni siquiera por Administrador (`has_delete_permission` devuelve `False`), con el mismo criterio de la Decisión 12 para `Validation`. El borrado será lógico al implementarse la Fase 3 (`deleted_at`). Por eso el seed no otorga `delete_commitment`.

**Verificado:** el funcionario de Norte ve solo su compromiso; el de Centro lo redirige; el POST manual con delegación o responsable ajeno se rechaza; la edición cruzada por POST directo deja el registro ajeno intacto; el Verificador recibe 403; el Administrador ve ambos y no puede borrar.

**Alternativa descartada — crear `delegado_demo`:** la rúbrica formativa pide "**al menos** 3" usuarios de prueba, así que un cuarto sería válido. Se descartó por costo/beneficio: para ser demostrable tendría que poder hacer algo que el Funcionario no (reasignar el responsable, HU-15, prioridad **P2**), lo que exige lógica propia en el `ModelAdmin` y más casos que probar; sin esa diferencia sería un usuario de adorno. Los 3 usuarios actuales ya cumplen "permisos diferentes y demostrables". El grupo `Delegado` sigue creado y sin permisos. **Pendiente para Eva 3:** reasignación de responsable y usuario `delegado_demo`.

**Sobre la Decisión 5:** esa decisión listaba 3 usuarios de prueba; la cantidad no cambia, solo se documenta qué puede hacer cada uno sobre las entidades nuevas.

---

### Decisión 19 — `requirements.txt` en UTF-8 (patch 5)

**Origen:** `requirements.txt` estaba guardado en UTF-16 little-endian con saltos CRLF (típico de `pip freeze > requirements.txt` en PowerShell de Windows). `pip` puede fallar al leerlo según la versión y la plataforma, y Linux (el destino del despliegue en AWS, paso 9.5) no lo interpreta bien.

**Decisión:** reescribirlo en UTF-8 con saltos LF. El contenido (5 dependencias) no cambia. **Al agregar dependencias nuevas (Pillow, `openpyxl`, Faker), no usar `>` de PowerShell**: usar `pip freeze | Out-File -Encoding utf8` o editar el archivo a mano.

---

## Verificación de alcance contra la rúbrica

Las 7 entidades escogidas (Delegación, Cargo, Funcionario, Período, Actividad, Evidencia, Validación) fueron confirmadas como necesarias y suficientes para cada criterio de esta evaluación:

| Criterio | Cómo se cubre |
|---|---|
| Admin Básico (4 maestras + 2 operativas) | 4 maestras + 3 operativas (por sobre el mínimo) |
| Inline | `ValidacionInline` en `EvidenciaAdmin` |
| Acción personalizada | Aprobar evidencias en lote, restringida al grupo `Verificador` (Decisión 9), y actualiza `estado_revision` (Decisión 9-bis) |
| Validación (`clean()`) | Fecha de `Actividad` dentro del rango de su `Periodo` |
| Seguridad / scoping | Vía `Funcionario.delegacion_id` → filtra `Actividad` y `Evidencia` por delegación del usuario logueado |

No se agregan entidades adicionales solo para "tener más" — cada una de las 7 tiene una función verificable en la rúbrica.

---

## Alcance de entidades (actualizado por la Decisión 14, corregido por la Decisión 15)

**Este apartado decía, hasta la Decisión 13, que las 7 entidades siguientes quedaban fuera de esta evaluación "por decisión de fasificación del proyecto — no por olvido". La Decisión 14 revirtió eso**, fijando como alcance 8 módulos sobre las 14 entidades del dominio completo. **La Decisión 15 aclara que ese alcance de 14 entidades corresponde a la Eva 3 (evaluación sumativa III, aún no entregada)**, y que la evaluación formativa en curso (`docs/Evaluacion_Formativa_U2_BackEnd_TI3V41_INACAP.md`) toma solo 3 de estas 7 candidatas. Se deja registro de cada cambio en vez de borrar el texto anterior sin dejar rastro, porque las tres entregas (Evaluación Sumativa II de Admin, esta evaluación formativa de integración, y la futura Eva 3) comparten el mismo repo y el mismo `decisiones.md`.

De las 7 entidades que antes figuraban fuera de alcance, estado real por la Decisión 15. **Actualización (patches 1–5): `Meta`, `ElementoCatalogo` y `Compromiso` ya existen en el repo** (ver Decisiones 16, 17 y 18); las otras 4 siguen sin construirse por ser alcance de Eva 3:

- `Meta` — **dentro del alcance de esta entrega formativa** (Decisión 15). Requerida antes de poder agregar `Activity.meta` (Decisión 14).
- `ElementoCatalogo` — **dentro del alcance de esta entrega formativa** (Decisión 15). Cuando exista, queda pendiente decidir si los 4 campos de clasificación de `Activity` (`activity_type`, `service`, `attention`, `sub_attention`, hoy texto libre — ver Decisión 4) migran a FK reales hacia ella; es el cambio más invasivo del lote porque toca datos ya cargados por el seed.
- `Compromiso` — **dentro del alcance de esta entrega formativa** (Decisión 15). Fuente de verdad de `Compromiso.delegacion` sin confirmar por el docente (ver Decisión 14) — sigue sin confirmar, pendiente para cuando se implemente.
- `Funcion` — **fuera de esta entrega formativa, alcance de Eva 3** (Decisión 15).
- `CargoFuncion` (tabla puente Cargo↔Función) — **fuera de esta entrega formativa, alcance de Eva 3** (Decisión 15).
- `Indicador` — **fuera de esta entrega formativa, alcance de Eva 3** (Decisión 15). Persistencia vs. cálculo al vuelo sin confirmar por el docente (ver Decisión 14).
- `Auditoria` — **fuera de esta entrega formativa, alcance de Eva 3** (Decisión 15).

El MER completo (14 entidades) sigue siendo el alcance acordado a futuro del repo, pero corresponde a la Eva 3 — el alcance vigente de la entrega en curso es el de la Decisión 15: 10 entidades (6 maestras + 4 operativas).

## Pendientes

- [x] ~~Definir la acción personalizada concreta de Admin Pro~~ → resuelto: aprobar evidencias en lote, restringida al grupo `Verificador` (Decisión 9).
- [ ] Confirmar reparto de las **fases del plan de trabajo** entre los 4 integrantes del equipo (pendiente fuera de esta conversación — no bloquea el inicio de Fase 1).
- [ ] **Nuevo, Decisión 14, alcance Eva 3 (ver Decisión 15):** reparto de los **8 módulos** (distinto del reparto de fases de arriba) entre los 4 integrantes. Queda explícitamente sin fijar, solo sugerido como 2 módulos por integrante. No bloquea la entrega formativa en curso, que usa el alcance de la Decisión 15.
- [ ] Revisar si, al incorporar `ElementoCatalogo` en una entrega futura, migrar los 4 campos de texto libre de `Actividad` hacia FK reales. **Avance (Decisión 16):** solo `attention` migró; quedan pendientes `activity_type`, `service` y `sub_attention` para Eva 3.
- [x] ~~Confirmar si `Meta`/`CargoFuncion` se incorporan en esta entrega~~ → **revertido por la Decisión 14**: sí se incorporan. Esta línea decía lo contrario hasta la Decisión 13; se mantiene tachada por trazabilidad histórica, no porque siga vigente. `Cargo`/`Position` deja de tener una sola relación activa una vez que exista `CargoFuncion`.
- [x] ~~Afinar tipos de datos definitivos de cada campo (`IntegerField` vs `PositiveIntegerField`, `FileField` vs `URLField`, etc.)~~ → `Evidencia.archivoOVinculo` resuelto como `FileField` (Decisión 7). Resto de tipos numéricos (`PositiveIntegerField` vs `IntegerField`) queda para revisión campo a campo al momento de escribir `models.py`.
- [x] ~~Definir política de `on_delete` en las FK~~ → resuelto: `PROTECT` por defecto, `CASCADE` solo en `Funcionario.user` y `Validacion.evidencia` (Decisión 8).
- [x] ~~**Nuevo, para Fase 3 (seed):** el default `PROTECT` (Decisión 8) implica que el orden de borrado/recreación de fixtures importa, y que un comando de seed no idempotente puede trabarse contra sus propias protecciones al re-ejecutarse sobre datos parcialmente cargados.~~ → resuelto: `core/management/commands/seed_sgr.py` usa `get_or_create` en la creación de grupos, delegaciones, cargos, usuarios, funcionarios, período, actividades, evidencias y validación — comando probado idempotente (dos corridas seguidas sin duplicar ni lanzar `ProtectedError`/`UNIQUE constraint failed`) y probado también desde base vacía (`db.sqlite3` borrado → `migrate` → `seed_sgr`, corre limpio). Reset documentado como único método soportado: borrar `db.sqlite3` y volver a migrar, nunca borrar filas sueltas desde el Admin.
- [x] ~~**Nuevo, para Fase 2 (settings/config):** configurar `MEDIA_URL` y `MEDIA_ROOT` en `settings.py`, y servir archivos de media en `urls.py` en desarrollo.~~ → resuelto en Fase 2, confirmado funcional en Fase 3: `Evidencia.archivo` sube y sirve archivos reales en el Admin (verificado manualmente — el PDF de cada Evidencia del seed se ve y descarga correctamente).
- [x] ~~Definir `related_name` de cada FK~~ → resuelto: convención plural/singular según cardinalidad, ver Decisión 10.
- [x] ~~**Nuevo, detectado en revisión cruzada de Fase 4/5/6:** definir si `Validacion` puede borrarse desde el Admin~~ → resuelto: nadie puede borrarla, ni siquiera `admin_sgr` (ver Decisión 12).
- [x] ~~**Nuevo, por evaluación formativa 2.1.1–2.1.4:** renombrar a inglés las 7 entidades de esta entrega y decidir la partición en apps Django~~ → resuelto: ver Decisión 13 (`accounts` / `organization` / `performance`).
- [ ] **Nuevo, por evaluación formativa 2.1.1–2.1.4:** diseñar e implementar login, logout y recuperación de contraseña por código de 6 dígitos (vive en `accounts`, que quedó sin modelos por la Decisión 13). Asignado como pieza de trabajo aparte de los 8 módulos del dominio completo — sin dueño confirmado todavía dentro del equipo.
- [ ] **Nuevo, por evaluación formativa 2.1.1–2.1.4:** definir qué entidades son "eliminables" (con `deleted_at` o equivalente) y el patrón de manager/queryset para excluirlas de listados normales — todavía no implementado en ninguna de las 7 entidades actuales, y la lista de candidatas crece con la Decisión 14 (probablemente sume `Compromiso`).
- [ ] **Nuevo, Decisión 14, sin confirmar por el docente (no tratar como resuelto):** si `Indicador` se persiste como tabla o se calcula al vuelo. Solo hay recomendación de tabla persistida con recálculo vía `services.py`.
- [ ] **Nuevo, Decisión 14, sin confirmar por el docente (no tratar como resuelto):** fuente de verdad de `Compromiso.delegacion` — FK directa vs. inferida del responsable. Solo hay sugerencia de que la FK directa sea la fuente de verdad, validada con `clean()`. **Implementada así en la Fase 2 (Decisión 17), pero sigue sin confirmar por el docente.**
- [ ] **Nuevo, Decisión 14:** si hay un mínimo de complejidad esperado por módulo — sigue sin respuesta del docente.
- [x] ~~**Nota de numeración:** si en una entrega futura se documenta la decisión de agregar `Actividad.meta`... debe numerarse **Decisión 14**, no 13~~ → resuelto: ver Decisión 14 arriba.
- [x] ~~**Nuevo, Decisión 15:** construir `Meta`, `ElementoCatalogo` y `Compromiso` (`models.py`, migraciones, registro en Django Admin)~~ → **resuelto en la Fase 2 (patches 1–5)**: las tres existen (`ElementoCatalogo` como `CatalogItem`, `Compromiso` como `Commitment`), con migraciones `0002`–`0006` y registro en Admin. `Activity.meta` (Decisión 14) también quedó implementada. Ver Decisiones 16, 17 y 18.
- [x] ~~**Nuevo, Decisión 15:** definir en qué app vive cada una de las 3 nuevas entidades~~ → **resuelto de hecho en la Fase 2**: las tres viven en `performance` (`CatalogItem`, `Meta`, `Commitment`), junto a `Period` y `Activity`, con las que se relacionan. Ninguna ameritó app propia.
- [ ] **Nuevo, Decisión 18:** implementar reasignación de responsable de un `Commitment` (HU-15, P2) y crear el usuario `delegado_demo` — el grupo `Delegado` existe pero sin permisos ni usuario de prueba. Alcance de Eva 3, no de la formativa.
- [ ] **Nuevo, Decisión 18:** el scoping por Delegación de `Commitment` está solo en el Admin. Debe replicarse en las vistas web de la Fase 6 (paso 5.1 del plan) si `Commitment` se elige entre los 4 CRUD.
- [ ] **Nuevo, Decisión 18:** cuando se implemente el borrado lógico (Fase 3), `Commitment` debe incluirse entre las entidades "eliminables"; hoy no se puede borrar de ninguna forma desde el Admin.
- [ ] **Nuevo, Decisión 17:** mecanismo de "excepción formalmente configurada" de RN-001 (suma de ponderadores = 100%) — no definido en ningún documento del proyecto; hoy `clean()` solo exige que no supere 100%.
- [ ] **Nuevo, Decisión 15:** repartir entre el equipo cuál de las 3 nuevas entidades (`Meta`, `ElementoCatalogo`, `Compromiso`) construye cada integrante — sin fijar todavía, análogo al pendiente de reparto de la Decisión 14 pero para el alcance de esta entrega formativa, no el de Eva 3.
