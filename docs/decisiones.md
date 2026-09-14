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

---

## Verificación de alcance contra la rúbrica

Las 7 entidades escogidas (Delegación, Cargo, Funcionario, Período, Actividad, Evidencia, Validación) fueron confirmadas como necesarias y suficientes para cada criterio de esta evaluación:

| Criterio | Cómo se cubre |
|---|---|
| Admin Básico (4 maestras + 2 operativas) | 4 maestras + 3 operativas (por sobre el mínimo) |
| Inline | `ValidacionInline` en `EvidenciaAdmin` |
| Acción personalizada | Ej.: aprobar evidencias seleccionadas / cerrar actividades de un período |
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

- [ ] Definir la acción personalizada concreta de Admin Pro (aprobar evidencias en lote / cerrar actividades por período — a decidir por el equipo).
- [ ] Confirmar reparto de las **fases del plan de trabajo** entre los 4 integrantes del equipo (pendiente fuera de esta conversación — no bloquea el inicio de Fase 1).
- [ ] Revisar si, al incorporar `ElementoCatalogo` en una entrega futura, migrar los 4 campos de texto libre de `Actividad` hacia FK reales.
- [ ] Confirmar si `Meta`/`CargoFuncion` (que hoy dejan a `Cargo` con una sola relación activa: `Cargo → Funcionario`) se incorporan en la siguiente entrega, según lo hablado.
- [ ] Afinar tipos de datos definitivos de cada campo (`IntegerField` vs `PositiveIntegerField`, `FileField` vs `URLField`, etc.) directamente en `models.py` durante Fase 2 — el `.puml` actual usa tipos genéricos a propósito.
