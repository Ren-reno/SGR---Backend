# Evaluación Sumativa 3 API RESTful con JWT

**Unidad de Aprendizaje 3 · Programación Back End · Sección vespertina**

| Campo | Dato | Campo | Dato |
|---|---|---|---|
| Área académica | Tecnologías de Información y Ciberseguridad | Carrera | Analista Programador / Ingeniería en Informática |
| Asignatura | Programación Back End | Código | TI3041 |
| Sede | La Serena | Docente | Javier Ahumada |
| Evaluación | N.º 3 vespertino · 30 % | Puntaje | 100 puntos |
| Fecha de entrega | Según Aula Virtual | Exigencia | 60 % para nota 4,0 |

**Nombre del estudiante:** ____________________________________________________ **Sección:** __________

**Proyecto y recurso a cargo:** _________________________________________________________________

**Puntaje obtenido:** __________ / 100 &nbsp;&nbsp; **Nota:** __________ &nbsp;&nbsp; **Fecha:** __________________

---

## Propósito y modalidad

Implemente una API RESTful con Django REST Framework sobre el proyecto que desarrolla su equipo. La evaluación N.º 3 de la sección vespertina considera seis modelos del dominio, datos de prueba, JWT, permisos y pruebas con Apidog. Cada integrante debe levantar el sistema y demostrarlo en su propio equipo del laboratorio, de manera individual, aunque el repositorio de desarrollo sea compartido.

### Aprendizaje esperado

- **3.1:** codificar una API RESTful para conexión con otras aplicaciones mediante JWT.

**Criterios:**
- 3.1.1 configura DRF
- 3.1.2 codifica autenticación
- 3.1.3 entrega JSON
- 3.1.4 construye una API RESTful funcional

---

## Alcance del proyecto y datos

Cada equipo adapta la solución a su propio problema. Los seis modelos exigidos son modelos de negocio del proyecto, declarados en Django y migrados. No cuentan como parte de los seis User, Group, Permission, Session ni tablas automáticas de Django.

| Tipo | Cantidad mínima | Qué representa y qué API se exige |
|---|---|---|
| Principales | 4 modelos | Entidades centrales del dominio. Cada una tendrá CRUD REST: lista, detalle, creación, actualización y eliminación según la regla del proyecto. |
| Operacionales | 2 modelos | Registran o apoyan una operación del sistema, por ejemplo evento, historial, asignación, detalle o alerta. Cada una tendrá al menos GET lista y GET detalle. |

Los seis modelos deben tener datos válidos y relaciones coherentes cuando correspondan. La base de prueba tendrá al menos **2.000 registros** de dominio en total; esa cantidad puede concentrarse en el modelo donde el volumen sea razonable, pero ningún modelo exigido puede quedar vacío. Prepare un comando de carga o fixture reproducible para poblarla sin ingresar registros manualmente durante la revisión.

Cree **tres usuarios normales** de prueba, distintos y activos. No use superusuarios para demostrar permisos:

- **Administrador API**: lectura y escritura
- **Operador API**: solo lectura
- **Usuario autenticado sin rol API**: sin acceso a los recursos

Puede usar los nombres de grupos que ya tenga el proyecto si respetan esta matriz.

---

## Requisitos técnicos verificables

- **DRF y recursos.** Configure serializers con campos explícitos, ViewSets o vistas REST equivalentes y rutas claras bajo `/api/`. Exponga CRUD para los cuatro modelos principales y lista/detalle para los dos operacionales. Proteja las seis rutas. Una eliminación lógica es válida si corresponde al dominio y se explica en el README.

- **JWT y roles.** Configure Simple JWT para obtener y renovar access token. Envíe access como Bearer. El administrador puede usar GET, POST, PUT/PATCH y DELETE en los modelos principales; el operador solo puede consultar; el tercero, aun autenticado, no puede consultar ni modificar. Las solicitudes sin token a los recursos protegidos deben dar 401 y las denegadas por rol, 403.

- **JSON, validaciones y estados.** Las rutas deben responder JSON en los casos aplicables. Implemente dos validaciones relevantes para el dominio, una de campo y otra de relación o regla de negocio. Demuestre 400 por datos inválidos, 404 por id inexistente, 200 para consultas/actualizaciones, 201 al crear y 204 al eliminar físicamente, o el estado documentado si usa otra semántica.

- **Volumen y paginación.** Una lista principal debe estar paginada y permitir consultar los datos cargados sin devolver los 2.000 registros en una sola respuesta. El README debe indicar tamaño de página y cómo solicitar otra página.

- **Entorno local.** El proyecto debe iniciar desde el repositorio con dependencias registradas, migraciones aplicables y una forma documentada de cargar los datos. No se exige URL pública ni despliegue en AWS para esta evaluación vespertina.

---

## Pruebas mínimas en Apidog

Cada integrante debe poder ejecutar la colección desde su servidor local. Registre URL, método, identidad, estado esperado y observado, y una respuesta representativa. Use datos ficticios y oculte JWT y contraseñas en las capturas o exportaciones.

| Comprobación | Solicitud o alcance | Identidad | Estado esperado |
|---|---|---|---|
| Cobertura de modelos | CRUD de las cuatro entidades principales; GET lista y detalle de las dos operacionales | Administrador / operador | 200, 201, 204 según método |
| JWT | Obtener token y renovar access | Administrador | 200 |
| Sin autenticación | GET de recurso protegido | Sin token | 401 |
| Solo lectura | GET y POST de una principal | Operador | 200 y 403 |
| Sin rol API | GET de recurso protegido | Tercer usuario | 403 |
| CRUD completo | POST, GET detalle, PATCH o PUT, DELETE | Administrador | 201, 200, 200, 204* |
| Errores | Dos validaciones e id inexistente | Administrador | 400, 400, 404 |
| Paginación | GET de dos páginas de recurso voluminoso | Operador | 200 y resultados distintos |

*Si el proyecto aplica borrado lógico, documente el estado de respuesta y demuestre que el registro deja de figurar en consultas normales. Para 401, use JWT como autenticador de las rutas evaluadas; otras configuraciones pueden devolver un estado distinto.

---

## Revisión presencial y entrega

- La revisión se realiza en el laboratorio, en la fecha indicada en Aula Virtual. Cada integrante abrirá su propia copia local del repositorio, iniciará el servidor, mostrará los seis modelos poblados, los tres usuarios y ejecutará las pruebas solicitadas por el docente. No basta con una demostración desde el computador de otro integrante.

- Entregue URL del repositorio, rama de trabajo y hash del commit evaluado. No haga commits directos a la rama principal durante el desarrollo; identifique su aporte y la integración del equipo.

- Incluya README con tabla de los seis modelos y sus relaciones, endpoints y métodos, roles, preparación del entorno, migraciones, comando o fixture de carga, total de registros y uso de Apidog. Adjunte colección exportada o matriz con evidencias. No suba `.env`, base local con datos personales, credenciales ni tokens vigentes.

- El docente podrá solicitar que ejecute casos adicionales y preguntarle por cualquier fragmento del código cuando tenga dudas sobre la autoría o el desarrollo. Cada estudiante debe explicar su propio aporte y el funcionamiento necesario para reproducirlo.

> La nota 4,0 se obtiene con 60 puntos de 100. Se calificará la evidencia que el estudiante logre ejecutar y explicar durante la revisión individual en laboratorio. La fecha y hora de entrega se publicarán en Aula Virtual.

---

## Rúbrica de evaluación — Escala de apreciación

Marque el nivel alcanzado en cada fila. Los seis criterios suman 100 puntos. La revisión combina el producto del equipo con la ejecución y explicación individual de cada integrante.

### Modelos y datos — 20 pts

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 20 | Cuatro modelos principales y dos operacionales coherentes, migrados y poblados; tres usuarios normales; al menos 2.000 registros reproducibles. |
| Habilitado | 14 | Seis modelos y usuarios presentes; carga o relaciones con un detalle menor. |
| En desarrollo | 7 | Faltan datos, volumen o algún modelo; la carga requiere intervención importante. |
| No logrado | 0 | No existe el conjunto mínimo de modelos y datos verificables. |

### Configuración DRF — 10 pts

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 10 | DRF, serializers, vistas y rutas de los seis recursos funcionan desde el entorno local. |
| Habilitado | 7 | Configuración funcional con un detalle menor de rutas o reproducción. |
| En desarrollo | 4 | Configuración parcial; varios recursos no se pueden consultar. |
| No logrado | 0 | No hay API DRF ejecutable. |

### API RESTful — 20 pts

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 20 | CRUD completo en cuatro principales, consulta de dos operacionales y paginación comprobada sobre datos persistidos. |
| Habilitado | 14 | Recursos funcionales con un método, consulta o detalle de paginación pendiente. |
| En desarrollo | 7 | CRUD incompleto en varios recursos o paginación ausente con el volumen exigido. |
| No logrado | 0 | No se demuestra una API RESTful operativa. |

### JSON y validación — 10 pts

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 10 | JSON consistente; dos validaciones relevantes; respuestas 400 y 404 correctas y explicadas. |
| Habilitado | 7 | JSON y errores adecuados; una validación o estado requiere un ajuste menor. |
| En desarrollo | 4 | Solo una validación o manejo parcial de respuestas y errores. |
| No logrado | 0 | No entrega JSON útil ni valida entradas. |

### JWT y permisos — 20 pts

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 20 | JWT access/refresh; seis recursos protegidos; administrador CRUD, operador lectura y tercero sin rol denegado; 401 y 403 demostrados. |
| Habilitado | 14 | Roles y JWT operativos con una falla menor en una ruta o prueba. |
| En desarrollo | 7 | Protección parcial o una escritura/lectura queda abierta a un usuario no autorizado. |
| No logrado | 0 | JWT o control por rol no funcionan. |

### Repositorio Git y levantamiento — 10 pts

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 10 | Repositorio permite clonar y levantar el proyecto en un entorno limpio siguiendo su documentación; incluye `requirements.txt`, `.gitignore`, `.env.example`, migraciones e instrucciones de carga de datos. No contiene `.env`, entorno virtual ni secretos. Historial Git permite identificar participación de los integrantes. |
| Habilitado | 7 | Proyecto se levanta desde el repositorio, pero requiere uno o dos ajustes menores de configuración, documentación o dependencias. |
| En desarrollo | 4 | Repositorio existe, pero el levantamiento requiere intervención importante, archivos no documentados o correcciones del docente/integrantes. |
| No logrado | 0 | Repositorio no disponible/verificable o el proyecto no puede levantarse desde lo entregado. |

### Apidog y defensa — 10 pts

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 10 | Colección cubre los seis recursos, roles, CRUD, errores, JWT y paginación. Cada estudiante ejecuta las pruebas, identifica y explica código relevante y demuestra comprensión de la solución. |
| Habilitado | 7 | Demostración reproducible y pruebas principales; faltan hasta dos casos o detalles menores de documentación/explicación. |
| En desarrollo | 4 | Pruebas aisladas o requiere apoyo importante de otro integrante para ejecutar y explicar la API. |
| No logrado | 0 | No logra demostrar la API ni presentar evidencia verificable. |
