# Evaluación Sumativa II: Taller "Aplicación web con Django Admin"

**Área Tecnologías de Información y Ciberseguridad**
**Ingeniería en Informática - Analista Programador**

---

## Datos generales

| Campo | Detalle | Campo | Detalle |
|---|---|---|---|
| **Área académica** | Informática y Telecomunicaciones | **Carrera** | Analista Programador / Ingeniería en Informática |
| **Asignatura** | Programación Back End | **Código** | TI3041 |
| **Sede** | La Serena | **Docente** | Javier Ahumada |
| **Unidad de Aprendizaje** | N° II | **Criterios a Evaluar** | (2.1.1, 2.1.2) |
| **Duración** | — | **Fecha** | — |

**Nombre del equipo / proyecto:** _____________________

**Integrantes:** _____________________

| Puntaje máximo | Puntaje obtenido | Nota |
|---|---|---|
| 100 | | |

**Solicita re-corrección:** Sí / No — **Motivo:** _____________________

---

## Instrucciones generales

1. La nota 4.0 se obtiene logrando un 60% del puntaje total.
2. La evaluación se desarrolla en equipo. La calificación corresponde al producto grupal, pero la verificación de comprensión se realiza mediante preguntas dirigidas a uno o más integrantes seleccionados por el docente.
3. Cada criterio posee una pregunta de verificación. Si el integrante seleccionado no logra identificar, explicar o demostrar la implementación solicitada, se descontará 1 punto del puntaje obtenido en ese criterio. El descuento se aplica una sola vez por criterio.
4. El proyecto debe presentarse en un computador del laboratorio institucional, desde un entorno limpio, utilizando el repositorio entregado y la configuración documentada.
5. El equipo debe entregar el sistema con información suficiente para demostrar todas las funcionalidades. La ausencia de datos no será subsanada por el docente durante la evaluación.

## Aprendizaje esperado

**2.1.-** Codifica aplicaciones web para dar soluciones tentativas a una problemática utilizando un framework del lado del servidor.

## Criterios de evaluación

- **2.1.1** Configura la conexión a una base de datos, según requerimiento.
- **2.1.2** Utiliza el administrador de Django, de acuerdo con los requerimientos.

---

## Objetivo

Cada equipo debe desarrollar, documentar y defender una aplicación web en Django que permita comprobar una base de datos correctamente configurada y un Django Admin funcional, personalizado y protegido según los requerimientos de su problemática.

## Requerimientos técnicos

1. **Conexión BD:** Configurar `settings.py` mediante variables de entorno (`.env`), aplicar migraciones sin errores y dejar el proyecto portable para ejecutarse en un computador distinto al de desarrollo.

2. **Usuarios y roles:** Crear como mínimo dos usuarios de prueba con permisos o contextos diferentes: un usuario administrador o con permisos completos y un usuario limitado.

3. **Admin Básico:** Registrar como mínimo 4 tablas maestras y 2 operativas. Configurar `list_display`, `search_fields`, `list_filter`, `ordering` y `list_select_related` cuando existan ForeignKey visibles.

4. **Admin Pro:** Implementar al menos un Inline, una acción personalizada útil para el dominio y una validación controlada mediante `clean()`, `ModelForm` o `InlineFormSet`.

5. **Seguridad:** EcoEnergy: aplicar scoping por organización. Otros proyectos: restringir datos y/o acciones según rol, área, propietario u otro criterio coherente con la problemática.

6. **Modelo e informe:** Incluir diagrama entidad-relación con tipos de datos y relaciones, modelos Django y evidencias de conexión, migraciones, Admin, Inline, acción, validación y seguridad.

7. **Reproducibilidad:** Incluir en el repositorio el mecanismo de carga de datos (fixture, seed o management command), `requirements.txt` y las instrucciones mínimas de ejecución en README.

> ### ⚠️ CARGA DE DATOS OBLIGATORIA
>
> - La carga debe contener, como mínimo, dos usuarios funcionales con permisos o contextos distintos y registros asociados que permitan comprobar la seguridad del sistema.
> - En proyectos multiempresa/multiorganización deben existir datos de al menos dos contextos diferentes para comprobar que un usuario no visualiza ni modifica información ajena.
> - Las credenciales utilizadas para la demostración deben ser cuentas de prueba documentadas; no se deben usar credenciales personales.
> - Si no existen datos suficientes para ejecutar una funcionalidad, dicha funcionalidad se considerará **NO DEMOSTRADA** y obtendrá **0 puntos** en el criterio correspondiente. El docente no creará, corregirá ni completará información durante la evaluación.

## Contenido mínimo del informe PDF

- Fragmento de `settings.py` que evidencie `DATABASES` y uso de variables de entorno.
- Diagrama ER y explicación breve de las tablas maestras y operativas.
- Usuarios/roles de prueba y evidencia de diferencias de acceso.
- Admin con columnas, búsqueda, filtros y ordenamiento.
- Inline funcionando, acción personalizada ejecutada y validación mostrando un error controlado.
- Evidencia de scoping/rol con datos reales de prueba.
- Descripción breve de cómo cargar los datos de prueba y levantar el proyecto.

---

## Revisión en vivo en laboratorio

En la fecha de entrega, el equipo deberá presentar y ejecutar el proyecto directamente en un computador del laboratorio institucional. La revisión debe comenzar desde el repositorio entregado y permitir comprobar el funcionamiento completo del Admin.

1. Clonar o descargar el repositorio indicado en la entrega.
2. Crear/activar el entorno virtual e instalar las dependencias requeridas.
3. Configurar el archivo `.env` a partir de `.env.example` o de las instrucciones documentadas.
4. Ejecutar migraciones.
5. Cargar las semillas/fixtures incluidas en el proyecto.
6. Ingresar con el usuario administrador y mostrar el Admin completo.
7. Cerrar sesión e ingresar con el usuario limitado para demostrar las restricciones.
8. Ejecutar búsqueda, filtros, Inline, acción, validación y scoping/rol sobre datos previamente cargados.

## Verificación mediante preguntas dirigidas

El docente podrá dirigir las preguntas a uno, varios o todos los integrantes del equipo. La persona seleccionada deberá localizar la implementación en el código, explicar su propósito y, cuando corresponda, demostrarla en ejecución.

- La pregunta está asociada al criterio evaluado y se refiere al proyecto entregado, no a definiciones memorizadas.
- Se podrá reformular la pregunta una vez para aclarar lo solicitado.
- Si el estudiante no identifica, no explica o desconoce la implementación propia, se descuenta 1 punto del criterio correspondiente.
- La respuesta del integrante seleccionado afecta el puntaje del criterio del equipo, ya que todos los integrantes deben conocer el trabajo presentado.
- El descuento por pregunta no puede reducir un criterio por debajo de 0 puntos.

> **IMPORTANTE:** La demostración funcional es responsabilidad del equipo. Presentar código sin datos que permitan probarlo no constituye evidencia suficiente de funcionamiento.

## Entregables

- Informe PDF: `U2_Eval2_<NombreProyecto>_<Seccion>.pdf`
- URL del repositorio Git y hash del último commit considerado para la evaluación.
- Proyecto con `migrations`, `requirements.txt`, `.env.example` y mecanismo reproducible de carga de datos.
- README con instrucciones de instalación/ejecución y cuentas de prueba necesarias para la demostración.
- Revisión y defensa presencial en laboratorio.

> **EL DOCENTE SE RESERVA EL DERECHO DE REALIZAR PREGUNTAS ADICIONALES SOBRE EL CÓDIGO EN CASO DE DUDAS DE AUTORÍA O INCONSISTENCIAS ENTRE LA ENTREGA Y LA DEMOSTRACIÓN.**

---

## Rúbrica de Evaluación

Puntaje máximo: 100 puntos. La pregunta de verificación asociada a cada criterio puede descontar 1 punto del puntaje obtenido en dicho criterio.

| Criterio | Destacado | Habilitado | En Desarrollo | Insuficiente |
|---|---|---|---|---|
| **Conexión BD + Migraciones**<br>9 pts | BD configurada mediante `.env`; migraciones y check correctos; el proyecto conecta en entorno limpio.<br>**9 pts** | Conecta y migra, pero requiere un ajuste menor de configuración o documentación.<br>**5 pts** | Conexión o migraciones funcionan solo parcialmente y requieren intervención importante.<br>**2 pts** | No conecta o no logra aplicar migraciones.<br>**0 pts** |
| **Admin Básico**<br>10 pts | 4+ tablas maestras y 2+ operativas; columnas, búsqueda, filtros, ordering y optimización de FK correctamente aplicados.<br>**10 pts** | Admin funcional con la mayoría de las configuraciones solicitadas; presenta omisiones menores.<br>**6 pts** | Modelos registrados, pero personalización básica o incompleta.<br>**3 pts** | Modelos no registrados o Admin no operativo.<br>**0 pts** |
| **Admin Pro**<br>22 pts | Inline, acción personalizada y validación están implementados, son coherentes con el dominio y funcionan con datos cargados.<br>**22 pts** | Implementa correctamente 2 de los 3 elementos o presenta un detalle menor en uno de ellos.<br>**14 pts** | Solo 1 elemento funciona o los tres presentan fallas relevantes.<br>**6 pts** | Sin evidencia funcional de Admin Pro.<br>**0 pts** |
| **Seguridad (scoping / rol)**<br>15 pts | Dos usuarios/contextos diferenciados; el limitado no ve ni modifica información no autorizada. Se demuestra con datos de ambos contextos.<br>**15 pts** | Roles/permisos funcionan, pero existe una omisión menor de visibilidad o acción.<br>**9 pts** | Restricciones parciales o inconsistentes; existe acceso indebido a alguna información/acción.<br>**4 pts** | Sin roles/scoping funcional o sin datos para demostrarlo.<br>**0 pts** |
| **Informe escrito**<br>15 pts | Diagrama ER, modelos, evidencias y explicaciones completas; las relaciones del diagrama corresponden al código implementado.<br>**15 pts** | Informe completo en lo esencial, con detalles menores faltantes.<br>**9 pts** | Informe parcial: faltan relaciones, capturas o explicaciones relevantes.<br>**4 pts** | Sin informe o evidencia insuficiente.<br>**0 pts** |
| **Revisión en vivo**<br>20 pts | Levanta el proyecto desde entorno limpio, configura `.env`, migra, carga datos reproducibles y demuestra Admin completo con ambos usuarios sin errores.<br>**20 pts** | Levanta y demuestra el proyecto, con detalles menores que no impiden la revisión.<br>**13 pts** | Dificultades importantes para instalar, migrar, cargar datos o demostrar varias funciones.<br>**6 pts** | No logra levantar el proyecto o la ausencia de datos impide la revisión funcional.<br>**0 pts** |
| **U2 · Avance Integrado y gestión Git**<br>9 pts | El avance fue entregado en plazo y es coherente con la versión final. El equipo utiliza ramas de trabajo para desarrollar funcionalidades o correcciones, evita commits directos sobre main, integra los cambios mediante merge o Pull Request y mantiene un historial comprensible con commits descriptivos. El hash informado corresponde a la versión evaluada y el repositorio no contiene archivos sensibles o innecesarios como `.env` o `.venv`.<br>**9 pts** | Utiliza ramas y existe integración hacia main, pero presenta una omisión menor: algunos commits poco descriptivos, uso parcial de Pull Request/merge, escasa separación de cambios o algún commit directo aislado sobre main.<br>**6 pts** | El repositorio existe, pero el trabajo se concentra mayoritariamente en main, hay poca evidencia de uso de ramas, los cambios se integran de manera poco clara o existe escasa trazabilidad del proceso.<br>**2 pts** | No existe evidencia de trabajo con ramas, todo el desarrollo fue realizado directamente sobre main, no se puede identificar la versión evaluada o el repositorio no permite verificar el proceso de desarrollo.<br>**0 pts** |

**Regla de descuento:** respuesta satisfactoria = mantiene el puntaje obtenido. Si, después de una reformulación breve, el estudiante no logra identificar, explicar o demostrar la implementación solicitada, se descuenta del criterio correspondiente.

## Condición de evaluabilidad

**La evaluación se realiza sobre un proyecto demostrable. Si una funcionalidad no puede comprobarse por ausencia de registros, usuarios de prueba, relaciones o datos necesarios, se considera no demostrada y recibe 0 puntos en el criterio asociado. Es responsabilidad del equipo preparar y verificar previamente la carga de información.**
