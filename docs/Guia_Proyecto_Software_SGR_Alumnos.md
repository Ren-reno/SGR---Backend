# GUÍA DE PROYECTO INTEGRADO

# Sistema de Gestión de Resultados (SGR)

*Especificación, Product Backlog, criterios de aceptación y plan de desarrollo*

*Caso académico: transformación de una necesidad municipal en un producto de software verificable.*

| | |
|---|---|
| **Institución** | INACAP |
| **Contexto del caso** | Delegaciones municipales - Ilustre Municipalidad de La Serena |
| **Uso** | Proyecto integrador para estudiantes de desarrollo e ingeniería de software |
| **Versión** | 1.0 - Documento académico consolidado |
| **Fecha** | 31 de agosto de 2026 |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 2 de 30*

## Contenido del documento maestro

**Orientaciones para el proyecto académico**

- Propósito y contexto
- Visión del sistema y alcance
- Actores y responsabilidades
- Flujo operativo general
- Requerimientos funcionales
- Requerimientos no funcionales
- Reglas de negocio y cálculos
- Información y entidades principales
- Criterios de aceptación integrales
- Supuestos, restricciones y decisiones pendientes
- Trazabilidad con la presentación fuente
- Product Backlog: épicas e historias de usuario
- Alcance mínimo y plan de implementación
- Arquitectura, seguridad y calidad técnica
- Entregables y evidencias del proyecto
- Ficha de entrega y control de version

**Propósito académico:** Este documento constituye la línea base del caso. Los equipos deben convertirla en diseño, código, base de datos, pruebas y una demostración funcional; no basta con reproducir planillas o pantallas estáticas.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 3 de 30*

## Orientaciones para el proyecto académico

El desafío consiste en desarrollar una aplicación web responsiva que centralice el registro, seguimiento, validación y medición de la gestión de funcionarios y delegaciones. La solución debe persistir información en una base de datos, aplicar reglas de negocio y demostrar controles básicos de seguridad.

### Resultado de aprendizaje esperado

1. Interpretar necesidades organizacionales y convertirlas en requisitos verificables.
2. Diseñar arquitectura, modelo de datos, interfaces y flujos coherentes con el alcance.
3. Implementar un incremento funcional priorizado mediante prácticas ágiles.
4. Aplicar validación, control de acceso, trazabilidad, pruebas y documentación técnica.
5. Presentar evidencia objetiva del cumplimiento de historias y criterios de aceptación.

### Condiciones del caso

| DIMENSIÓN | DEFINICIÓN PARA EL PROYECTO |
|---|---|
| Producto esperado | Aplicación web responsiva con frontend, lógica de negocio, API o backend, base de datos y almacenamiento controlado de evidencias. |
| Tecnología | El equipo puede proponer el stack, sujeto a aprobación docente y a que permita demostrar seguridad, persistencia, pruebas y despliegue. |
| Datos | Solo se utilizarán datos ficticios o anonimizados. Está prohibido cargar información real de ciudadanos o funcionarios. |
| Priorización | P1 corresponde al alcance mínimo recomendado; P2 y P3 se incorporan según tiempo, complejidad y definición docente. |
| Trabajo de equipo | Cada integrante debe aportar evidencia trazable en repositorio, tablero de tareas, documentación y demostración. |

**Regla de interpretación:** Si una historia contradice un requerimiento formal, prevalece el requerimiento y debe registrarse la decisión. Las ambigüedades no se resuelven silenciosamente: se documentan como supuestos o consultas al docente.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 4 de 30*

## 1. Propósito y contexto

El presente documento convierte la Matriz SGR descrita en la presentación fuente en una especificación formal y verificable. Su propósito es servir como base para validar el proceso actual, diseñar una solución digital o evolucionar la implementación existente en Google Workspace.

### 1.1 Problema identificado

- Las delegaciones operan con criterios y registros independientes, dificultando una visión transversal.
- No existe un registro consolidado de solicitudes, actividades, compromisos y servicios entregados.
- Las tareas, metas y ponderaciones no se encuentran formalizadas en una herramienta única.
- La jefatura requiere indicadores oportunos para acompañar a los equipos y controlar compromisos.
- La evidencia de ejecución debe quedar asociada a cada actividad y ser validada.

### 1.2 Objetivo general

**Objetivo:** Centralizar el registro, seguimiento, verificación y medición de la gestión de funcionarios y delegaciones, generando indicadores individuales y colectivos que apoyen el control operativo y la toma de decisiones.

### 1.3 Objetivos específicos

- Registrar las actividades ejecutadas por cada funcionario.
- Gestionar compromisos futuros mediante una agenda colectiva.
- Mantener una base de datos de servicios y atenciones entregadas.
- Definir funciones, metas, ponderaciones y períodos de medición.
- Vincular evidencias verificables con las actividades registradas.
- Calcular avances, cumplimientos ponderados y semáforos diarios.
- Presentar resúmenes por funcionario, cargo, delegación y organización.

## 2. Visión del sistema y alcance

### 2.1 Alcance funcional

| COMPONENTE | COBERTURA |
|---|---|
| Administración | Delegaciones, funcionarios, roles, cargos, funciones, catálogos, períodos y parámetros. |
| Registro individual | Actividades, solicitudes, problemas, acciones, contactos, servicios e ingreso a agenda colectiva. |
| Evidencias | Código único, fotografía asociada, revisión, validación y resultado. |
| Agenda colectiva | Compromisos, responsables, fechas, estados, observaciones y seguimiento. |
| Medición | Metas, ponderadores, avance, cumplimiento, puntaje ponderado, incentivos y penalizaciones. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 5 de 30*

| COMPONENTE | COBERTURA |
|---|---|
| Monitoreo | Semáforo diario, indicadores personales, resumen colectivo y resumen de delegación. |
| Información | Búsqueda, filtros, informes, exportaciones y trazabilidad de cambios. |

### 2.2 Fuera de alcance inicial

- Gestión presupuestaria, contable o de remuneraciones.
- Evaluación formal de desempeño laboral o decisiones de recursos humanos sin validación institucional adicional.
- Atención ciudadana multicanal completa, firma electrónica o tramitación documental integral.
- Integraciones con sistemas municipales no identificadas en la presentación.

**Criterio de alcance:** La plataforma puede conservar Google Workspace como base operativa o evolucionar a una aplicación web. Esta decisión tecnológica debe validarse antes del diseño de solución.

### 2.3 Vista conceptual

| 1. Registrar | 2. Clasificar | 3. Verificar | 4. Calcular | 5. Decidir |
|---|---|---|---|---|
| Actividad o compromiso | Ítem, servicio y responsable | Evidencia y validación | Avance y ponderación | Semáforo e informe |

*Infografía 1. Flujo de valor de la Matriz SGR.*

## 3. Actores y responsabilidades

| ACTOR | RESPONSABILIDAD PRINCIPAL |
|---|---|
| Administrador | Configura delegaciones, usuarios, cargos, catálogos, períodos, metas, ponderaciones y permisos. |
| Coordinador del sistema | Supervisa la operación transversal, revisa indicadores, resuelve criterios y coordina mejoras. |
| Delegado o jefatura | Consulta la gestión de su delegación, asigna o revisa compromisos y acompaña el cumplimiento. |
| Funcionario | Registra actividades, compromisos, avances, contactos, servicios y evidencias asociadas. |
| Verificador | Revisa evidencias, valida o rechaza registros y deja trazabilidad de su decisión. |
| Usuario de consulta | Accede a tableros e informes según el ámbito autorizado, sin modificar datos operativos. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*

**Principio de acceso:** Cada actor debe visualizar y modificar únicamente la información necesaria para su función, delegación y nivel de responsabilidad.

## 4. Flujo operativo general

### 4.1 Registro y validación de una actividad

| | | |
|---|---|---|
| **01** | **Ingreso** | El funcionario registra fecha, actividad, acción, contacto y clasificación. |
| **02** | **Código** | El sistema genera un identificador único para la evidencia. |
| **03** | **Evidencia** | Se adjunta o referencia una fotografía asociada al código. |
| **04** | **Revisión** | El verificador aprueba o rechaza y registra observaciones. |
| **05** | **Resultado** | El registro validado actualiza avance, cumplimiento e indicadores. |

*Infografía 2. Ciclo de registro, evidencia y puntuación.*

### 4.2 Agenda colectiva o tubo de trabajo

1. Registrar un compromiso futuro originado por una solicitud o actividad.
2. Definir solicitante, territorio, responsable, fecha comprometida y área de apoyo.
3. Actualizar el estado entre Ingresado, Pendiente, En proceso y Realizado.
4. Registrar observaciones de avance y comunicar cambios cuando no sea posible cumplir la fecha.
5. Consolidar porcentajes por funcionario y por delegación.

RURAL ▾ | Calendario ▾ | TUBO ▾ | T OC ▾ | G. SOCIAL ▾ | AP ADM. ▾ | SUP DISERCO ▾ | COOR DISERCO ▾
COOR DISERCO ▾ | PROY COM ▾ | PLAN y CON ▾ | G. SEG ▾ | RECLAMOS ▾ | SEMAFORO ▾ | 🔒 RESUMEN ▾

*Referencia visual de módulos o pestañas identificados en la solución actual.*

## 5. Requerimientos funcionales

**Convención:** Alta = imprescindible para operar el proceso; Media = necesaria para control o eficiencia. La columna Fuente identifica las diapositivas que originan o respaldan el requerimiento.

### 5.1 Configuración organizacional y de medición

| ID | REQUERIMIENTO | NIVEL | CRITERIO DE ACEPTACIÓN |
|---|---|---|---|
| RF-001 | Administrar delegaciones. El sistema deberá crear, modificar, activar y desactivar delegaciones o unidades organizacionales. | Alta | Alta de una delegación con nombre único y disponibilidad inmediata en filtros y asignaciones. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 7 de 30*

| ID | REQUERIMIENTO | NIVEL | CRITERIO DE ACEPTACIÓN |
|---|---|---|---|
| RF-002 | Administrar usuarios y roles. El sistema deberá mantener funcionarios, estado, cargo, delegación y uno o más roles autorizados. | Alta | Un administrador asigna un funcionario a una delegación y el acceso refleja el rol otorgado. |
| RF-003 | Configurar cargos y funciones. El sistema deberá asociar a cada cargo las funciones e ítems que serán medidos. | Alta | Al seleccionar un cargo se cargan únicamente sus ítems de medición vigentes. |
| RF-004 | Mantener catálogo de actividades y servicios. El sistema deberá administrar tipos de actividad, servicio, atención y subatención por área. | Alta | Los catálogos pueden actualizarse sin alterar registros históricos. |
| RF-005 | Configurar períodos de medición. El sistema deberá definir fecha de inicio, fecha de término, estado y días computables de cada período. | Alta | El período calcula sus días y rechaza una fecha de término anterior al inicio. |
| RF-006 | Configurar ponderaciones. El sistema deberá asignar un porcentaje de ponderación a cada ítem de un cargo y período. | Alta | La configuración se guarda solo cuando la suma aplicable cumple la regla definida. |
| RF-007 | Configurar metas y umbrales. El sistema deberá mantener metas por ítem, umbral mínimo de cumplimiento, máximo computable y reglas del semáforo. | Alta | El cambio queda versionado y rige desde el período seleccionado. |

### 5.2 Registro personal y evidencias

| ID | REQUERIMIENTO | NIVEL | CRITERIO DE ACEPTACIÓN |
|---|---|---|---|
| RF-008 | Presentar ficha personal. El sistema deberá mostrar funcionario, cargo, delegación, ítems, metas, avance y cumplimiento ponderado. | Alta | La ficha consolida datos del período actual y permite consultar períodos anteriores. |
| RF-009 | Registrar actividades. El funcionario deberá registrar fecha, actividad/solicitud/problema, acción, contacto, teléfono, ítem y relación con la agenda colectiva. | Alta | El sistema guarda un registro válido y muestra confirmación e identificador. |
| RF-010 | Validar campos de actividad. El sistema deberá controlar obligatoriedad, formatos y coherencia de fechas, teléfonos, ítems y estados. | Alta | Un registro incompleto no se guarda y se informa el campo que requiere corrección. |
| RF-011 | Generar código de evidencia. Al registrar una actividad, el sistema deberá generar un código único utilizable para nombrar y vincular su evidencia. | Alta | Dos actividades nunca reciben el mismo código y el código permanece inmutable. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 8 de 30*

| ID | REQUERIMIENTO | NIVEL | CRITERIO DE ACEPTACIÓN |
|---|---|---|---|
| RF-012 | Asociar evidencia. El sistema deberá adjuntar o referenciar fotografías y otros archivos permitidos a una actividad mediante su código. | Alta | La evidencia queda visible desde la actividad y conserva fecha y autor de carga. |
| RF-013 | Validar evidencia. Un verificador autorizado deberá aprobar, rechazar o solicitar corrección de una evidencia, registrando observación. | Alta | La validación identifica verificador, fecha, resultado y comentario. |
| RF-014 | Controlar puntuación por validación. El sistema deberá incorporar al avance únicamente las actividades que cumplan la condición de validación establecida. | Alta | Una evidencia rechazada no aumenta el avance; al aprobarla el indicador se recalcula. |
| RF-015 | Registrar atención social secuenciada. El área social deberá registrar hasta tres gestiones o atenciones asociadas a una misma persona usuaria, con tipos y fechas diferenciadas. | Alta | El caso muestra su secuencia completa sin duplicar la identificación principal del usuario. |

### 5.3 Agenda colectiva

| ID | REQUERIMIENTO | NIVEL | CRITERIO DE ACEPTACIÓN |
|---|---|---|---|
| RF-016 | Crear compromisos en agenda colectiva. El sistema deberá registrar compromisos futuros derivados de solicitudes internas o externas. | Alta | El compromiso queda disponible para los actores autorizados de la delegación. |
| RF-017 | Asignar compromiso. Cada compromiso deberá incluir solicitante, territorio, responsable, área de apoyo y fecha comprometida. | Alta | El sistema impide guardar sin responsable y fecha cuando sean obligatorios. |
| RF-018 | Gestionar estados. El sistema deberá permitir transiciones controladas entre Ingresado, Pendiente, En proceso y Realizado. | Alta | Cada cambio conserva estado anterior, nuevo estado, autor, fecha y observación. |
| RF-019 | Controlar plazos. El sistema deberá identificar compromisos próximos a vencer, vencidos y realizados fuera de plazo. | Alta | Un compromiso vencido sin cierre aparece destacado en agenda y resumen. |
| RF-020 | Relacionar agenda y medición. El cumplimiento de compromisos deberá alimentar el indicador individual cuando el ítem así lo configure. | Alta | Al cerrar un compromiso validado se actualiza el ítem correspondiente una sola vez. |
| RF-021 | Generar resumen colectivo. El sistema deberá totalizar compromisos por funcionario y estado, incluyendo porcentaje realizado y pendiente. | Alta | Los totales coinciden con el detalle filtrado del mismo período. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 9 de 30*

### 5.4 Cálculos, semáforos y tableros

| ID | REQUERIMIENTO | NIVEL | CRITERIO DE ACEPTACIÓN |
|---|---|---|---|
| RF-022 | Calcular avance actual. El sistema deberá contabilizar las actividades válidas por ítem, funcionario, delegación y período. | Alta | El valor cambia automáticamente cuando se valida o anula un registro. |
| RF-023 | Calcular porcentaje de cumplimiento. El sistema deberá calcular el avance respecto de la meta definida para cada ítem. | Alta | Para meta mayor que cero, el resultado corresponde a avance dividido por meta y se expresa en porcentaje. |
| RF-024 | Calcular cumplimiento ponderado. El sistema deberá multiplicar el porcentaje de cumplimiento por el ponderador aplicable, respetando el máximo configurado. | Alta | La suma de resultados por ítem coincide con el total ponderado personal. |
| RF-025 | Aplicar incentivos y penalizaciones. El sistema deberá parametrizar conceptos adicionales positivos o negativos, como felicitaciones y reclamos. | Media | Cada ajuste indica motivo, valor, responsable y efecto en el resultado. |
| RF-026 | Calcular meta esperada al día. El sistema deberá determinar el avance acumulado esperado según días transcurridos y duración del período. | Alta | La meta diaria cambia con la fecha del sistema y no supera el 100 % del período. |
| RF-027 | Mostrar semáforo de avance. El sistema deberá clasificar el avance de cada funcionario en verde, ámbar o rojo según umbrales configurables. | Alta | El color se actualiza al cambiar el avance, la fecha o los umbrales. |
| RF-028 | Mostrar tablero personal. El sistema deberá presentar metas, avance, cumplimiento, ponderación, estado de evidencias y compromisos del funcionario. | Alta | El tablero permite filtrar por período y consultar el detalle origen del indicador. |
| RF-029 | Mostrar tablero de delegación. El sistema deberá consolidar responsables, avance, semáforo, meta esperada, promedio y resultado global. | Alta | El total de la delegación se obtiene de los registros de sus funcionarios. |
| RF-030 | Medir actividad reciente. El sistema deberá mostrar fecha del último ingreso, días sin ingreso, cantidad de registros y promedio diario por funcionario. | Media | Los indicadores se recalculan al registrar una actividad válida. |
| RF-031 | Mostrar vista global por cargos. El sistema deberá presentar cargos, funcionarios, fechas relevantes, metas y cifras logradas por equipo. | Media | La vista permite navegar desde el resumen hasta el detalle de un cargo o funcionario. |

### 5.5 Consulta, colaboración y administración

| ID | REQUERIMIENTO | NIVEL | CRITERIO DE ACEPTACIÓN |
|---|---|---|---|

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 10 de 30*

| ID | REQUERIMIENTO | NIVEL | CRITERIO DE ACEPTACIÓN |
|---|---|---|---|
| RF-032 | Buscar y filtrar información. El sistema deberá filtrar por delegación, área, funcionario, cargo, período, ítem, estado y rango de fechas. | Alta | El resultado de cada filtro coincide con los registros que cumplen los criterios seleccionados. |
| RF-033 | Generar y exportar informes. El sistema deberá generar informes actualizados y exportarlos en formatos definidos por la institución. | Media | La exportación conserva filtros, fecha de generación y encabezados legibles. |
| RF-034 | Permitir trabajo simultáneo. La plataforma deberá aceptar registros concurrentes de varias delegaciones sin sobrescribir información. | Alta | Dos usuarios pueden guardar registros distintos simultáneamente y ambos permanecen íntegros. |
| RF-035 | Facilitar coordinación. El sistema deberá permitir observaciones o comentarios asociados a registros para resolver dudas operativas. | Media | La conversación conserva autor, fecha y referencia al registro correspondiente. |
| RF-036 | Mantener trazabilidad. El sistema deberá registrar altas, modificaciones, validaciones, cambios de estado y ajustes de parámetros. | Alta | Un usuario autorizado puede consultar quién cambió qué dato y cuándo. |
| RF-037 | Emitir alertas. El sistema debería alertar por vencimientos, evidencias pendientes, ausencia de registros y avance bajo el umbral. | Media | La alerta identifica motivo, responsable, fecha y enlace al elemento afectado. |
| RF-038 | Versionar parámetros. El sistema deberá conservar la vigencia histórica de metas, ponderadores, catálogos y reglas de cálculo. | Alta | Un cambio de configuración no modifica resultados cerrados de períodos anteriores. |

## 6. Requerimientos no funcionales

**Importante:** Los valores cuantitativos propuestos deben ajustarse de acuerdo con cantidad de usuarios, criticidad, infraestructura y acuerdos institucionales.

| ID | ATRIBUTO | REQUERIMIENTO |
|---|---|---|
| RNF-001 | Disponibilidad | La solución deberá estar disponible durante la jornada operativa y registrar indisponibilidades. Meta inicial propuesta: 99,5 % mensual, por validar. |
| RNF-002 | Rendimiento | Las operaciones de registro y consulta deberán responder en un máximo objetivo de 2 segundos en condiciones normales; tableros consolidados, hasta 5 segundos. |
| RNF-003 | Concurrencia | La solución deberá soportar trabajo simultáneo sin pérdida, duplicación ni sobrescritura silenciosa de datos. |
| RNF-004 | Autenticación | Todo acceso deberá requerir identidad individual; se recomienda integración con el directorio institucional y autenticación multifactor. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 11 de 30*

| ID | ATRIBUTO | REQUERIMIENTO |
|---|---|---|
| RNF-005 | Autorización | Los permisos deberán aplicarse por rol, delegación, función y operación, siguiendo mínimo privilegio y segregación de funciones. |
| RNF-006 | Confidencialidad | Las comunicaciones deberán usar cifrado seguro y los repositorios deberán proteger datos y evidencias durante almacenamiento y respaldo. |
| RNF-007 | Integridad | La solución deberá validar formatos, relaciones, duplicados y cambios concurrentes antes de confirmar una operación. |
| RNF-008 | Auditoría | Los eventos críticos deberán conservar usuario, fecha, origen, acción, valor anterior y valor nuevo, con protección contra alteración no autorizada. |
| RNF-009 | Privacidad | Se deberán minimizar los datos personales, restringir su visualización y establecer conservación y eliminación conforme a la normativa y políticas institucionales aplicables. |
| RNF-010 | Respaldo y recuperación | La información deberá respaldarse de forma automatizada. Valores iniciales propuestos: RPO de 24 horas y RTO de 4 horas, sujetos a validación. |
| RNF-011 | Usabilidad | Las pantallas deberán emplear etiquetas comprensibles, validación contextual, filtros consistentes y diseño adaptado a tareas frecuentes. |
| RNF-012 | Accesibilidad | La interfaz deberá considerar navegación por teclado, contraste suficiente, textos alternativos y criterios de accesibilidad institucional vigentes. |
| RNF-013 | Compatibilidad | La solución web deberá operar en versiones institucionalmente soportadas de Chrome y Edge, en equipos de escritorio y dispositivos móviles. |
| RNF-014 | Escalabilidad | La arquitectura deberá permitir incorporar nuevas delegaciones, cargos, actividades, períodos y usuarios sin rediseñar el modelo. |
| RNF-015 | Mantenibilidad | Metas, ponderadores, estados, catálogos y umbrales deberán configurarse sin cambios de código para ajustes operativos habituales. |
| RNF-016 | Interoperabilidad | La solución deberá permitir exportación estructurada y dejar preparada la integración futura mediante interfaces controladas. |
| RNF-017 | Gestión de evidencias | Se deberán definir formatos, tamaño máximo, antivirus, metadatos, acceso, retención y eliminación segura de archivos. |
| RNF-018 | Monitoreo | La operación deberá generar métricas y alertas sobre errores, fallas de integración, capacidad y tareas automáticas. |

## 7. Reglas de negocio y cálculos

| ID | REGLA |
|---|---|
| RN-001 | La suma de ponderadores aplicables a un cargo y período deberá ser 100 %, salvo excepción formalmente configurada. |
| RN-002 | La meta de un ítem cuantitativo deberá ser mayor que cero; los ítems porcentuales deberán declarar su fórmula específica. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 12 de 30*

| ID | REGLA |
|---|---|
| RN-003 | Avance actual = cantidad o resultado de actividades válidas asociadas al ítem durante el período. |
| RN-004 | % de cumplimiento = avance actual / meta del período x 100. La presentación denomina este valor como diferencia, pero los ejemplos corresponden a una razón; debe validarse. |
| RN-005 | Cumplimiento ponderado = ponderador x % de cumplimiento. El máximo observado es 150 %, parámetro que deberá confirmarse. |
| RN-006 | El umbral mínimo de cumplimiento colectivo indicado en la presentación es 80 %. Deberá ser configurable por período o indicador. |
| RN-007 | Meta esperada al día = días transcurridos computables / días totales computables x 100, con tratamiento definido para fecha inicial y final. |
| RN-008 | Semáforo propuesto: verde si avance >= meta esperada; ámbar si avance >= 60 % de la meta esperada y menor que ella; rojo si avance < 60 %. Confirmar umbrales. |
| RN-009 | Solo una validación aprobada puede otorgar el punto de logro; una evidencia rechazada o anulada no deberá contabilizarse. |
| RN-010 | Los códigos de evidencia deberán ser únicos, inmutables y mantener relación uno a uno o uno a muchos según el tipo de actividad. |
| RN-011 | Felicitaciones, reclamos u otros ajustes deberán tener valores parametrizables. La presentación muestra penalizaciones de -20 % y -30 %, por lo que se requiere definición oficial. |
| RN-012 | Una atención social podrá registrar hasta tres gestiones relacionadas para la misma persona usuaria, conservando fechas y resultados por etapa. |
| RN-013 | Los períodos cerrados no podrán modificarse salvo reapertura autorizada y auditada. |

### 7.1 Interpretación visual del semáforo

| | |
|---|---|
| **VERDE** | Avance igual o superior a la meta acumulada esperada al día. |
| **ÁMBAR** | Avance entre el 60 % y menos del 100 % de la meta esperada al día. |
| **ROJO** | Avance inferior al 60 % de la meta esperada al día. |

*Infografía 3. Regla de semáforo propuesta; requiere validación funcional.*

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 13 de 30*

**META SEGUN AVANCE DEL DIA**

| | |
|---|---|
| 56 | 61,54% |
| 26 ago 2026 | 100% |

**META SEGUN AVANCE DEL DIA**

| | |
|---|---|
| FECHA INICIO | 1/07/2026 |
| FECHA TERMINO | 30/09/2026 |
| DIAS | 91 |
| PORCENTAJE DIARIO | 1,10% |

*Referencia del cálculo diario incluida en la presentación fuente.*

## 8. Información y entidades principales

| ENTIDAD | DATOS MÍNIMOS |
|---|---|
| Delegación | Identificador, nombre, estado, responsables y ámbito. |
| Funcionario | Identificador institucional, nombre, cargo, delegación, roles y estado. |
| Cargo y función | Cargo, ítems medibles, servicios, ponderaciones y vigencia. |
| Período | Inicio, término, días computables, estado, umbrales y versión de parámetros. |
| Meta | Ítem, funcionario/cargo, valor objetivo, unidad y ponderador. |
| Actividad | Fecha, solicitud/problema, acción, contacto, teléfono, ítem, autor y estado. |
| Compromiso | Origen, solicitante, territorio, responsable, fecha, apoyo, estado y observación. |
| Evidencia | Código, archivo o vínculo, actividad, autor, fecha, metadatos y estado de revisión. |
| Validación | Verificador, decisión, fecha, observación, resultado y versión. |
| Indicador | Meta, avance, cumplimiento, ponderación, ajuste, semáforo y fecha de cálculo. |
| Auditoría | Usuario, evento, fecha, entidad, identificador, valor anterior y valor nuevo. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 14 de 30*

### 8.1 Campos mínimos del registro de actividad

- Número o identificador del registro.
- Fecha de la actividad.
- Actividad, solicitud o problema atendido.
- Acción ejecutada.
- Nombre o referencia de contacto y teléfono, cuando corresponda.
- Indicador de ingreso a la agenda colectiva.
- Ítem, servicio, tipo y subtipo de atención.
- Código de evidencia, archivo asociado, resultado y estado de validación.

**Protección de datos:** Las capturas de la presentación contienen nombres, teléfonos y otros identificadores. La solución deberá definir necesidad, base de acceso, visibilidad, conservación y eliminación de estos datos antes de su puesta en producción.

## 9. Criterios de aceptación integrales

| ID | ESCENARIO | RESULTADO ESPERADO |
|---|---|---|
| CA-01 | Registro validado | Dado un funcionario habilitado, cuando registra una actividad completa y un verificador aprueba su evidencia, entonces el avance del ítem aumenta una vez y los tableros se actualizan. |
| CA-02 | Evidencia rechazada | Cuando una evidencia es rechazada, el sistema conserva la observación y la actividad no aporta puntaje hasta su corrección y aprobación. |
| CA-03 | Compromiso vencido | Cuando vence la fecha de un compromiso no realizado, este aparece destacado, mantiene historial y genera la alerta configurada. |
| CA-04 | Atención social | Un caso social permite registrar tres gestiones diferenciadas y consultar la secuencia completa desde un único caso. |
| CA-05 | Cálculo diario | Al cambiar la fecha o el avance, la meta acumulada y el semáforo se recalculan de acuerdo con las reglas vigentes. |
| CA-06 | Consolidación | Los totales del tablero de delegación coinciden con la suma de registros válidos del detalle para el mismo filtro. |
| CA-07 | Control de acceso | Un funcionario no puede modificar datos de otra delegación salvo que su rol y ámbito lo autoricen explícitamente. |
| CA-08 | Concurrencia | Dos usuarios pueden registrar simultáneamente sin perder datos ni sobrescribir cambios sin advertencia. |
| CA-09 | Historial | Cada modificación crítica puede rastrearse hasta usuario, fecha, valor anterior y valor nuevo. |
| CA-10 | Período cerrado | Un usuario operativo no puede alterar resultados de un período cerrado; toda reapertura requiere autorización y auditoría. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 15 de 30*

## 12. Product Backlog: épicas e historias de usuario

El backlog consolida los documentos de épicas e historias de usuario y los alinea con la especificación formal. Se conservaron las 25 historias originales y se agregaron seis historias para cubrir administración, catálogos, períodos, filtros, auditoría y alertas.

**Formato:** Como [rol], quiero [capacidad], para [beneficio]. Cada historia incluye prioridad inicial, trazabilidad con requisitos y criterios de aceptación en formato Dado/Cuando/Entonces.

| ÉPICA | NOMBRE | HISTORIAS | ALCANCE MÍNIMO |
|---|---|---|---|
| EP-01 | Registro y gestión de actividades | HU-01 a HU-04 | 3 historias P1 |
| EP-02 | Medición y desempeño | HU-05 a HU-08 | 3 historias P1 |
| EP-03 | Evidencias y verificación | HU-09 a HU-11 | 3 historias P1 |
| EP-04 | Agenda colectiva y compromisos | HU-12 a HU-15 | 3 historias P1 |
| EP-05 | Monitoreo y control de gestión | HU-16 a HU-19 | 3 historias P1 |
| EP-06 | Reportabilidad y toma de decisiones | HU-20 a HU-22 | 1 historia P1 |
| EP-07 | Plataforma colaborativa | HU-23 a HU-25 | 2 historias P1 |
| EP-08 | Administración, seguridad y trazabilidad | HU-26 a HU-31 | 5 historias P1 |

### 12.1 Convención de prioridad

| Prioridad | Interpretación |
|---|---|
| P1 - Esencial | Necesaria para demostrar el flujo principal, integridad de datos y control del sistema. |
| P2 - Importante | Amplía la operación, colaboración, monitoreo o experiencia de uso. |
| P3 - Evolutiva | Funcionalidad analítica o de madurez que puede incorporarse después del MVP. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 16 de 30*

### 12.2 EP-01 - Registro y gestión de actividades

**Objetivo de la épica:** Centralizar actividades, solicitudes, servicios y funciones asociadas a los cargos.

#### HU-01. Registro de actividades

**Prioridad:** P1 | **Requisitos relacionados:** RF-009, RF-010, RF-014, RF-022

Como Funcionario, quiero registrar diariamente las actividades que realizo, para mantener evidencia de mi trabajo y aportar a la medición de mi gestión.

**Criterios de aceptación**

- Dado que el funcionario está autenticado, cuando registra una actividad completa, entonces el sistema almacena fecha, descripción, acción, contacto e indicador asociado.
- Dada una actividad registrada, cuando se consulta el historial, entonces el registro permanece disponible según los permisos del usuario.
- Dada una actividad asociada a un indicador, cuando su evidencia es aprobada, entonces aporta una sola vez al avance de la meta correspondiente.

#### HU-02. Registro de compromisos ciudadanos

**Prioridad:** P1 | **Requisitos relacionados:** RF-016 a RF-021

Como Funcionario, quiero registrar las solicitudes y compromisos adquiridos con los vecinos, para realizar seguimiento y asegurar su cumplimiento.

**Criterios de aceptación**

- Dado un compromiso nuevo, cuando se ingresa, entonces registra solicitante, responsable, territorio, fecha comprometida y descripción.
- Dado un compromiso registrado, cuando se consulta, entonces muestra su estado, responsable, fecha y observaciones vigentes.
- Dado un compromiso vencido que no está realizado, cuando se consulta la agenda o el resumen, entonces aparece destacado como vencido.

#### HU-03. Registro de servicios entregados

**Prioridad:** P2 | **Requisitos relacionados:** RF-004, RF-015

Como Funcionario del área social o territorial, quiero registrar los servicios y atenciones entregadas a las personas usuarias, para disponer de un historial actualizado de atención.

**Criterios de aceptación**

- Dada una persona atendida, cuando se registra una atención, entonces queda asociada al caso o identificador definido.
- Dadas varias atenciones para una misma persona, cuando se consulta el historial, entonces se visualiza su secuencia completa sin duplicar el caso principal.
- Dada una atención válida, cuando se genera un informe, entonces se considera una sola vez en las estadísticas correspondientes.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 17 de 30*

#### HU-04. Administración de funciones por cargo

**Prioridad:** P1 | **Requisitos relacionados:** RF-003, RF-006, RF-007

Como Supervisor o coordinador, quiero definir funciones e indicadores asociados a cada cargo, para evaluar la gestión mediante criterios previamente configurados.

**Criterios de aceptación**

- Dado un cargo existente, cuando el administrador lo configura, entonces puede asociarle funciones, indicadores, metas y ponderaciones.
- Dado un funcionario asignado a un cargo, cuando inicia un período, entonces recibe los ítems vigentes definidos para ese cargo.
- Dada una actualización de funciones, cuando se guarda, entonces rige desde la vigencia indicada y no modifica períodos cerrados.

### 12.3 EP-02 - Medición y desempeño

**Objetivo de la épica:** Configurar metas y calcular resultados personales y colectivos de manera reproducible.

#### HU-05. Definición de metas

**Prioridad:** P1 | **Requisitos relacionados:** RF-005 a RF-007

Como Coordinador, quiero asignar metas e indicadores medibles a cada cargo o funcionario, para evaluar el cumplimiento esperado durante un período.

**Criterios de aceptación**

- Dado un período de medición abierto, cuando el coordinador crea una meta, entonces informa valor objetivo, unidad, ponderación y vigencia.
- Dada una meta vigente, cuando se consulta, entonces muestra objetivo, avance, porcentaje de cumplimiento y resultado ponderado.
- Dada una modificación de meta, cuando se confirma, entonces se registra la versión, autor, fecha y período de aplicación.

#### HU-06. Seguimiento de avance

**Prioridad:** P1 | **Requisitos relacionados:** RF-008, RF-022, RF-023, RF-028

Como Funcionario, quiero visualizar mi avance respecto de las metas definidas, para conocer mi nivel de cumplimiento y gestionar mis actividades.

**Criterios de aceptación**

- Dado un funcionario autenticado, cuando accede a su panel, entonces visualiza metas, avance, cumplimiento y estado de evidencias del período seleccionado.
- Dadas nuevas actividades aprobadas, cuando se actualiza el panel, entonces los indicadores se recalculan automáticamente.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 18 de 30*

- Dada una meta alcanzada, cuando se consulta, entonces se muestra como cumplida sin ocultar el detalle que originó el resultado.

#### HU-07. Cálculo automático de cumplimiento

**Prioridad:** P1 | **Requisitos relacionados:** RF-023 a RF-026

Como Coordinador, quiero calcular automáticamente porcentajes y ponderaciones, para reducir errores y disponer de indicadores confiables.

**Criterios de aceptación**

- Dada una meta mayor que cero y una ponderación vigente, cuando existen avances aprobados, entonces el sistema calcula el cumplimiento y su aporte ponderado.
- Dado un nuevo registro aprobado o anulado, cuando cambia el avance, entonces los indicadores afectados se recalculan.
- Dado un reporte de desempeño, cuando se genera, entonces permite verificar meta, avance, fórmula, ponderación y resultado.

#### HU-08. Visualización del desempeño organizacional

**Prioridad:** P2 | **Requisitos relacionados:** RF-029, RF-031

Como Delegado, quiero visualizar el desempeño individual y grupal de la delegación, para identificar brechas y oportunidades de mejora.

**Criterios de aceptación**

- Dado un delegado autorizado, cuando accede al panel, entonces visualiza indicadores individuales y globales de su ámbito.
- Dados varios funcionarios, cuando se consulta el resumen, entonces se permite comparar resultados utilizando el mismo período y reglas.
- Dada una delegación seleccionada, cuando se revisa el resumen, entonces el total coincide con el detalle filtrado de sus funcionarios.

### 12.4 EP-03 - Evidencias y verificación

**Objetivo de la épica:** Respaldar la ejecución y separar el registro de la decisión de validación.

#### HU-09. Registro de evidencia fotográfica

**Prioridad:** P1 | **Requisitos relacionados:** RF-012, RNF-017

Como Funcionario, quiero adjuntar evidencias a las actividades realizadas, para demostrar su ejecución de forma verificable.

**Criterios de aceptación**

- Dada una actividad registrada, cuando el funcionario adjunta un archivo permitido, entonces la evidencia queda vinculada al código de la actividad.
- Dada una evidencia almacenada, cuando un usuario autorizado consulta la actividad, entonces puede visualizarla o descargarla.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 19 de 30*

- Dada una carga inválida, cuando el archivo supera el tamaño o no cumple el formato permitido, entonces se rechaza y se informa el motivo.

#### HU-10. Generación de códigos verificadores

**Prioridad:** P1 | **Requisitos relacionados:** RF-011

Como Funcionario, quiero obtener un identificador único por actividad, para vincular y localizar sus evidencias de respaldo.

**Criterios de aceptación**

- Dada una actividad nueva válida, cuando se guarda, entonces se genera un identificador único e inmutable.
- Dada una evidencia, cuando se carga, entonces puede vincularse únicamente a una actividad existente mediante su identificador.
- Dado un código conocido, cuando se busca, entonces se obtiene la actividad asociada si el usuario posee autorización.

#### HU-11. Validación de actividades

**Prioridad:** P1 | **Requisitos relacionados:** RF-013, RF-014, RF-036

Como Verificador, quiero aprobar, rechazar o solicitar corrección de una evidencia, para controlar qué actividades aportan al resultado.

**Criterios de aceptación**

- Dada una actividad con evidencia pendiente, cuando el verificador la revisa, entonces puede aprobarla, rechazarla o solicitar corrección.
- Dada una decisión de validación, cuando se guarda, entonces registra verificador, fecha, resultado y observación.
- Dada una actividad rechazada, cuando se consulta, entonces muestra el motivo y no aporta al avance hasta ser corregida y aprobada.

### 12.5 EP-04 - Agenda colectiva y compromisos

**Objetivo de la épica:** Coordinar compromisos futuros, estados, plazos y continuidad operativa.

#### HU-12. Agenda compartida

**Prioridad:** P1 | **Requisitos relacionados:** RF-016, RF-017

Como Funcionario, quiero registrar compromisos futuros en una agenda colectiva, para informar al equipo sobre las actividades programadas.

**Criterios de aceptación**

- Dado un compromiso nuevo, cuando se registra, entonces queda visible para los usuarios autorizados de su ámbito.
- Dada una actividad futura, cuando se consulta la agenda, entonces se muestra ordenada o agrupada por fecha.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 20 de 30*

- Dados varios compromisos, cuando se aplican filtros, entonces se puede acotar por responsable, estado, territorio y rango de fechas.

#### HU-13. Actualización de estados

**Prioridad:** P1 | **Requisitos relacionados:** RF-018, RF-036

Como Funcionario, quiero actualizar el estado de un compromiso, para mantener informada a la organización sobre su avance.

**Criterios de aceptación**

- Dado un compromiso registrado, cuando cambia su situación, entonces un usuario autorizado puede modificarlo entre los estados permitidos.
- Dado un cambio de estado, cuando se guarda, entonces conserva estado anterior, nuevo estado, autor, fecha y observación.
- Dado un compromiso realizado, cuando se consulta, entonces refleja su cierre y no aparece como pendiente.

#### HU-14. Seguimiento de compromisos

**Prioridad:** P1 | **Requisitos relacionados:** RF-019, RF-021, RF-037

Como Delegado, quiero monitorear compromisos pendientes, próximos a vencer y vencidos, para gestionar oportunamente los incumplimientos.

**Criterios de aceptación**

- Dados compromisos vigentes, cuando el delegado abre el resumen, entonces visualiza pendientes, próximos a vencer, vencidos y realizados.
- Dado un compromiso próximo a vencer, cuando alcanza el umbral configurado, entonces aparece destacado y puede generar una alerta.
- Dado un incumplimiento, cuando se identifica, entonces se conserva su estado e historial para seguimiento.

#### HU-15. Continuidad operativa

**Prioridad:** P2 | **Requisitos relacionados:** RF-017, RF-036

Como Delegado, quiero consultar y reasignar compromisos de funcionarios ausentes, para asegurar la continuidad del servicio.

**Criterios de aceptación**

- Dado un funcionario ausente, cuando el delegado consulta la agenda, entonces visualiza sus compromisos dentro de su ámbito.
- Dadas actividades asignadas, cuando otro funcionario las consulta, entonces accede solo si sus permisos lo autorizan.
- Dada una reasignación autorizada, cuando se confirma, entonces conserva responsable anterior, nuevo responsable, autor, fecha y motivo.

### 12.6 EP-05 - Monitoreo y control de gestión

**Objetivo de la épica:** Detectar desviaciones, resumir resultados y monitorear el uso de la solución.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 21 de 30*

#### HU-16. Semáforo de cumplimiento

**Prioridad:** P1 | **Requisitos relacionados:** RF-026, RF-027

Como Funcionario, quiero visualizar un semáforo de avance diario, para saber si mi progreso está dentro del nivel esperado.

**Criterios de aceptación**

- Dado un período vigente, cuando se calcula el avance esperado al día, entonces el sistema presenta un estado visual.
- Dado un avance inferior al 60 % de lo esperado, cuando se visualiza el indicador, entonces se muestra en rojo.
- Dado un avance entre el 60 % y menos del 100 % de lo esperado, entonces se muestra ámbar; si es igual o superior a lo esperado, se muestra verde.

#### HU-17. Comparación entre avance esperado y real

**Prioridad:** P1 | **Requisitos relacionados:** RF-023, RF-026, RF-027

Como Coordinador, quiero comparar el avance real con el esperado, para detectar desviaciones tempranas.

**Criterios de aceptación**

- Dado un período, cuando transcurren días computables, entonces el sistema calcula el porcentaje de avance esperado.
- Dado un avance real, cuando se compara con lo esperado, entonces se muestra la diferencia y el estado del semáforo.
- Dada una desviación significativa, cuando se detecta, entonces queda visible para el funcionario y los supervisores autorizados.

#### HU-18. Resumen ejecutivo

**Prioridad:** P1 | **Requisitos relacionados:** RF-028, RF-029, RF-031

Como Delegado, quiero consultar un panel resumen de indicadores, para disponer de una visión rápida del estado de la delegación.

**Criterios de aceptación**

- Dada información consolidada, cuando el delegado ingresa al panel, entonces visualiza indicadores clave del período y ámbito seleccionados.
- Dados datos actualizados, cuando se abre o refresca el panel, entonces se muestran los últimos resultados disponibles.
- Dada una consulta de gestión, cuando se visualiza el resumen, entonces permite navegar desde el total hacia el detalle autorizado.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 22 de 30*

#### HU-19. Control de actividad de usuarios

**Prioridad:** P2 | **Requisitos relacionados:** RF-030, RF-037

Como Supervisor, quiero consultar la fecha del último registro y frecuencia de uso, para detectar ausencia de actividad en la herramienta.

**Criterios de aceptación**

- Dado un funcionario, cuando se consulta su actividad, entonces se muestra la fecha de su último registro válido.
- Dados registros históricos, cuando se visualiza el resumen, entonces se muestra la cantidad y promedio diario del período.
- Dada una ausencia de registros que supera el umbral configurado, cuando ocurre, entonces se destaca en el resumen o genera una alerta.

### 12.7 EP-06 - Reportabilidad y toma de decisiones

**Objetivo de la épica:** Producir información filtrable, exportable y explicable para el análisis de gestión.

#### HU-20. Generación de informes

**Prioridad:** P1 | **Requisitos relacionados:** RF-032, RF-033

Como Coordinador, quiero obtener información consolidada de la gestión, para elaborar informes de desempeño y resultados.

**Criterios de aceptación**

- Dados registros del sistema, cuando se genera un informe, entonces se consolida únicamente la información que cumple el período y filtros seleccionados.
- Dado un informe generado, cuando se exporta, entonces mantiene encabezados, filtros aplicados, fecha de generación e integridad de datos.
- Dados distintos perfiles, cuando solicitan un informe, entonces el contenido respeta el ámbito y permisos de cada usuario.

#### HU-21. Identificación de funcionarios rezagados

**Prioridad:** P2 | **Requisitos relacionados:** RF-027, RF-029, RF-037

Como Delegado, quiero identificar resultados bajo el umbral definido, para apoyar oportunamente la mejora de la gestión.

**Criterios de aceptación**

- Dados indicadores vigentes, cuando se analizan, entonces se identifican los resultados bajo el umbral configurado.
- Dado un resultado rezagado, cuando se visualiza, entonces se presenta junto con sus metas, avances y registros de origen.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 23 de 30*

- Dada una mejora que alcanza el nivel esperado, cuando se recalcula el indicador, entonces deja de aparecer en el seguimiento de rezago.

#### HU-22. Identificación de brechas de productividad

**Prioridad:** P3 | **Requisitos relacionados:** RF-031, RF-038

Como Jefatura o coordinación, quiero analizar tendencias históricas frente a los objetivos del cargo, para detectar brechas sustentadas en información objetiva.

**Criterios de aceptación**

- Dados períodos históricos cerrados, cuando se analizan, entonces se comparan utilizando la versión de reglas que correspondía a cada período.
- Dada una brecha identificada, cuando se visualiza, entonces se presenta el detalle objetivo que origina el resultado.
- Dado un reporte de tendencia, cuando se genera, entonces incluye períodos comparados, filtros y resultados sin adoptar decisiones automáticas de recursos humanos.

### 12.8 EP-07 - Plataforma colaborativa

**Objetivo de la épica:** Permitir operación simultánea, coordinación contextual y adaptación controlada.

#### HU-23. Trabajo colaborativo en línea

**Prioridad:** P1 | **Requisitos relacionados:** RF-034, RNF-003

Como Funcionario, quiero trabajar simultáneamente con otros usuarios, para mantener datos actualizados sin pérdida ni sobrescritura silenciosa.

**Criterios de aceptación**

- Dados múltiples usuarios conectados, cuando guardan registros distintos, entonces ambos cambios permanecen íntegros.
- Dada una modificación confirmada, cuando otro usuario consulta el registro, entonces visualiza su versión actualizada.
- Dadas modificaciones concurrentes del mismo registro, cuando existe conflicto, entonces el sistema lo controla o informa antes de sobrescribir.

#### HU-24. Comunicación entre delegaciones

**Prioridad:** P2 | **Requisitos relacionados:** RF-035

Como Coordinador, quiero registrar observaciones o consultas asociadas a un registro, para resolver dudas y coordinar acciones con contexto.

**Criterios de aceptación**

- Dada una consulta asociada a un registro, cuando se envía, entonces queda visible para los participantes autorizados.
- Dada una respuesta, cuando se registra, entonces conserva autor, fecha y referencia al elemento correspondiente.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 24 de 30*

- Dadas interacciones entre usuarios, cuando se consultan, entonces se presenta la conversación en orden cronológico.

#### HU-25. Adaptación continua

**Prioridad:** P1 | **Requisitos relacionados:** RF-038

Como Administrador, quiero modificar indicadores, ponderadores y estructuras de medición, para adaptar el sistema sin perder la historia.

**Criterios de aceptación**

- Dado un administrador autorizado, cuando modifica un parámetro, entonces el sistema guarda el cambio y su vigencia.
- Dada una nueva necesidad, cuando se configura un indicador, entonces queda disponible para los períodos futuros seleccionados.
- Dadas modificaciones de configuración, cuando se aplican, entonces no alteran los resultados cerrados de períodos anteriores.

### 12.9 EP-08 - Administración, seguridad y trazabilidad

**Objetivo de la épica:** Cubrir las brechas detectadas al contrastar las historias originales con la especificación formal.

#### HU-26. Administración de delegaciones, usuarios y roles

**Prioridad:** P1 | **Requisitos relacionados:** RF-001, RF-002, RNF-004, RNF-005

Como Administrador, quiero gestionar unidades, usuarios, cargos y roles, para controlar el acceso según responsabilidad y ámbito.

**Criterios de aceptación**

- Dada una delegación, cuando el administrador la crea, modifica o desactiva, entonces el cambio se refleja en futuras asignaciones sin eliminar su historia.
- Dado un usuario activo, cuando se asigna a una delegación y rol, entonces sus permisos corresponden al ámbito otorgado.
- Dado un usuario sin autorización, cuando intenta consultar o modificar información fuera de su ámbito, entonces el acceso se deniega y el evento se registra.

#### HU-27. Administración de catálogos

**Prioridad:** P1 | **Requisitos relacionados:** RF-004

Como Administrador, quiero mantener catálogos de actividades, servicios, tipos y subtipos, para estandarizar la clasificación de los registros.

**Criterios de aceptación**

- Dado un elemento de catálogo, cuando se crea o modifica, entonces se valida que su nombre o código sea único dentro del catálogo.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 25 de 30*

- Dado un elemento utilizado históricamente, cuando se desactiva, entonces no puede seleccionarse en registros nuevos y permanece en los anteriores.
- Dado un formulario que usa un catálogo, cuando se abre, entonces muestra solo las opciones activas y aplicables al área correspondiente.

#### HU-28. Administración de períodos

**Prioridad:** P1 | **Requisitos relacionados:** RF-005, RN-013

Como Coordinador, quiero crear, abrir y cerrar períodos de medición, para aplicar reglas y fechas consistentes a los cálculos.

**Criterios de aceptación**

- Dado un período nuevo, cuando se configura, entonces la fecha de término es posterior o igual a la fecha de inicio y se calculan sus días computables.
- Dado un período abierto, cuando se registra actividad dentro de su vigencia, entonces puede aportar a sus indicadores según las reglas definidas.
- Dado un período cerrado, cuando un usuario operativo intenta modificar sus resultados, entonces la operación se rechaza; toda reapertura exige autorización y auditoría.

#### HU-29. Búsqueda y filtros

**Prioridad:** P1 | **Requisitos relacionados:** RF-032

Como Usuario autorizado, quiero buscar y filtrar información por criterios operativos, para encontrar rápidamente registros y verificar los indicadores.

**Criterios de aceptación**

- Dados registros existentes, cuando se aplican filtros por delegación, funcionario, período, ítem, estado o fechas, entonces el resultado contiene solo coincidencias autorizadas.
- Dado un conjunto filtrado, cuando se accede al detalle, entonces se conservan los criterios de búsqueda aplicados.
- Dado un usuario con ámbito restringido, cuando busca información, entonces no obtiene registros fuera de su autorización.

#### HU-30. Auditoría de cambios

**Prioridad:** P1 | **Requisitos relacionados:** RF-036, RNF-008

Como Administrador o auditor, quiero consultar el historial de operaciones críticas, para saber quién cambió qué dato y cuándo.

**Criterios de aceptación**

- Dada una operación crítica, cuando se ejecuta, entonces se registra usuario, fecha, acción, entidad, identificador, valor anterior y valor nuevo cuando corresponda.
- Dado un usuario autorizado, cuando consulta la auditoría, entonces puede filtrar eventos sin modificar ni eliminar los registros.
- Dada una alteración no autorizada del historial, cuando se intenta, entonces la operación se deniega y queda registrada.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 26 de 30*

#### HU-31. Alertas operativas

**Prioridad:** P2 | **Requisitos relacionados:** RF-037

Como Supervisor, quiero recibir alertas sobre vencimientos, evidencias pendientes y avance bajo el umbral, para actuar antes de que el incumplimiento se consolide.

**Criterios de aceptación**

- Dado un evento configurado, cuando se cumple su condición, entonces se genera una alerta con motivo, responsable, fecha y enlace al elemento afectado.
- Dada una alerta activa, cuando el usuario la atiende, entonces puede marcarla como revisada sin eliminar el evento original.
- Dada una regla de alerta, cuando el administrador modifica destinatarios o umbrales, entonces el cambio se aplica desde su vigencia y queda auditado.

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 27 de 30*

## 13. Alcance mínimo y plan de implementación

### 13.1 Definiciones funcionales para el prototipo académico

Para evitar que las contradicciones detectadas en la fuente bloqueen el desarrollo, se establece la siguiente línea base académica. Todo valor debe implementarse como parámetro cuando así se indica.

| REGLA | LÍNEA BASE ACADÉMICA |
|---|---|
| Período | Se configura con fecha de inicio y término. El sistema calcula los días computables; no se codifica de forma fija un período de 90 o 91 días. |
| Cumplimiento | cumplimiento (%) = avance aprobado / meta del período x 100. La meta debe ser mayor que cero. |
| Tope | El máximo académico inicial es 150 %, pero debe ser configurable y visible en la parametrización. |
| Ponderación | resultado ponderado = ponderador x cumplimiento (%) / 100. La suma de ponderadores aplicables debe ser 100 %. |
| Meta esperada al día | días computables transcurridos / días computables totales x 100. |
| Semáforo | Verde: avance >= esperado; ámbar: avance >= 60 % del esperado y < esperado; rojo: avance < 60 % del esperado. |
| Umbral colectivo | Se propone 80 % como valor inicial configurable. |
| Evidencias | Solo una actividad con validación aprobada aporta al avance. Un rechazo conserva motivo e historial. |
| Ajustes | Bonificaciones o penalizaciones no se codifican con valores fijos hasta que exista una regla parametrizada y aprobada. |

### 13.2 Alcance mínimo recomendado (MVP)

- Autenticación y autorización por rol y delegación.
- Administración básica de usuarios, cargos, catálogos, períodos, metas y ponderaciones.
- Registro de actividades con identificador único, evidencia y flujo de validación.
- Agenda colectiva con responsables, estados, plazos e historial de cambios.
- Cálculo de avance, cumplimiento ponderado, meta esperada al día y semáforo.
- Panel personal y resumen de delegación con filtros y acceso al detalle.
- Informe o exportación básica y auditoría de operaciones críticas.

### 13.3 Ruta sugerida de desarrollo

| FASE | FOCO | RESULTADO VERIFICABLE |
|---|---|---|
| Sprint 0 | Descubrimiento y diseño | Backlog refinado, prototipo, arquitectura, modelo de datos, repositorio y plan de pruebas. |
| Sprint 1 | Acceso y configuración | Autenticación, roles, delegaciones, usuarios, cargos, catálogos, períodos y metas. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 28 de 30*

| FASE | FOCO | RESULTADO VERIFICABLE |
|---|---|---|
| Sprint 2 | Operación principal | Actividades, código, evidencias, validación y agenda colectiva. |
| Sprint 3 | Medición y consulta | Cálculos, semáforo, paneles, filtros e informes. |
| Sprint 4 | Calidad y entrega | Pruebas, seguridad, correcciones, despliegue, manuales y demostración. |

## 14. Arquitectura, seguridad y calidad técnica

### 14.1 Arquitectura lógica recomendada

| Interfaz | API y aplicación | Dominio | Datos y archivos |
|---|---|---|---|
| Web responsiva | Controladores y servicios | Reglas y cálculos | BD y evidencias |

*Infografía 5. Separación lógica sugerida; el equipo debe justificar su arquitectura concreta.*

### 14.2 Controles mínimos de seguridad

| ÁREA | CONTROL EXIGIDO |
|---|---|
| Identidad | Contraseñas con algoritmo de hash seguro; sesiones protegidas; cierre de sesión; no almacenar claves en texto plano. |
| Autorización | Validar permisos en el servidor por rol, delegación y operación; ocultar botones no reemplaza el control de acceso. |
| Entradas | Validar tipo, longitud, formato, obligatoriedad y relaciones; usar consultas parametrizadas o un ORM de forma segura. |
| Archivos | Permitir formatos definidos, limitar tamaño, generar nombres seguros y evitar ejecución o exposición directa de cargas. |
| Errores | Mostrar mensajes comprensibles sin revelar consultas, rutas internas, credenciales ni trazas técnicas al usuario final. |
| Auditoría | Registrar operaciones críticas y proteger el historial contra modificación por usuarios operativos. |
| Secretos | Mantener credenciales y llaves en variables de entorno o mecanismos equivalentes; excluirlas del control de versiones. |
| Datos de prueba | Utilizar información sintética y aplicar mínimo privilegio en ambientes de demostración. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 29 de 30*

### 14.3 Estrategia mínima de pruebas

| TIPO | COBERTURA ESPERADA |
|---|---|
| Unitarias | Fórmulas, umbrales, transiciones de estado, validadores y servicios de dominio. |
| Integración | Persistencia, autenticación, autorización, carga de evidencias y actualización de indicadores. |
| Aceptación | Escenarios Dado/Cuando/Entonces priorizados para cada historia implementada. |
| Seguridad | Acceso horizontal/vertical, inyección, sesiones, archivos, errores y exposición de información. |
| Usabilidad | Flujos principales en escritorio y dispositivo móvil, mensajes y navegación por teclado básica. |

## 15. Entregables y evidencias del proyecto

| N° | ENTREGABLE | CONTENIDO MÍNIMO |
|---|---|---|
| 01 | Repositorio | Código fuente, historial de cambios, estrategia de ramas, archivo de exclusiones y README. |
| 02 | Análisis | Backlog priorizado, supuestos, decisiones, alcance del MVP y trazabilidad con requisitos. |
| 03 | Diseño | Prototipo de interfaces, arquitectura lógica, modelo de datos y principales diagramas de interacción. |
| 04 | Implementación | Aplicación ejecutable, base de datos, scripts o migraciones, configuración y datos ficticios de demostración. |
| 05 | Pruebas | Plan, casos, resultados y evidencias de pruebas funcionales, integración y seguridad. |
| 06 | Documentación | Manual de instalación/despliegue, manual breve de usuario y decisiones técnicas relevantes. |
| 07 | Demostración | Presentación del producto, recorrido de historias implementadas, resultados y limitaciones conocidas. |

### 15.1 Evidencia de trazabilidad

**Matriz exigida:** Cada equipo deberá mantener una matriz con: HU, requisito relacionado, tarea o commit, caso de prueba, resultado, responsable y enlace a la evidencia. Una historia no se considera terminada si no puede demostrarse su trazabilidad.

### 15.2 Criterios generales de revisión

| DIMENSIÓN | QUÉ SE REVISARÁ |
|---|---|
| Cobertura | Las funcionalidades presentadas corresponden al alcance acordado y cumplen sus criterios. |
| Coherencia | Interfaces, datos, reglas, estados y cálculos producen resultados consistentes. |

---

*PROYECTO SGR | GUÍA PARA ESTUDIANTES*
*Documento académico • Página 30 de 30*

| DIMENSIÓN | QUÉ SE REVISARÁ |
|---|---|
| Calidad técnica | El código está organizado, es mantenible, controla errores y evita duplicación innecesaria. |
| Seguridad | La solución aplica controles de identidad, acceso, validación, archivos, secretos y auditoría. |
| Pruebas | La evidencia permite reproducir casos normales, alternativos y de error. |
| Comunicación | El equipo explica decisiones, limitaciones, responsabilidades y aprendizajes con precisión técnica. |

### 15.3 Lista de comprobación previa a la entrega

- La aplicación puede instalarse o ejecutarse siguiendo el README.
- No existen contraseñas ni datos reales en el repositorio, base o capturas.
- Las cuentas de demostración tienen roles diferenciados.
- Los cálculos pueden verificarse con un conjunto de datos conocido.
- Las historias presentadas poseen prueba y evidencia trazable.
- Las limitaciones conocidas se encuentran declaradas y no ocultas.
- Todos los integrantes conocen el producto y pueden explicar su aporte.
