# Evaluación Formativa - Unidad II

## Integración Django: autenticación, permisos, CRUD, archivos y despliegue

| Campo | Valor |
|---|---|
| **Área académica** | Tecnologías de Información y Ciberseguridad |
| **Carrera** | Analista Programador / Ingeniería en Informática |
| **Asignatura** | Programación Back End |
| **Código / Sección** | TI3V41 |
| **Sede** | La Serena |
| **Docente** | Javier Ahumada |
| **Unidad** | N° II |
| **Criterios** | 2.1.1 · 2.1.2 · 2.1.3 · 2.1.4 |
| **Tipo** | Evaluación Formativa |
| **Puntaje referencial** | 100 puntos |
| **Duración** | _______________ |
| **Fecha** | _______________ |

---

## Instrucciones generales

1. La actividad es formativa. El puntaje es referencial y se utiliza para retroalimentación y preparación de la evaluación sumativa.
2. El trabajo es grupal; todos los integrantes deben comprender el proyecto completo y el código integrado.
3. Se debe presentar URL del repositorio, hash del último commit integrado y URL pública del despliegue en AWS Academy.
4. No se deben versionar `.env`, entornos virtuales, contraseñas, llaves ni secretos. Deben existir `.env.example`, `requirements.txt` y `README.md`.
5. Después del primer push de inicialización, el desarrollo debe realizarse mediante ramas y posterior integración; no se acepta trabajo habitual directo sobre `main`.
6. El docente podrá interrogar sobre el código. Si un integrante no explica una implementación presentada como propia, el descuento se aplicará al criterio técnico correspondiente.

---

## Aprendizaje esperado

**2.1** Codifica aplicaciones web para dar soluciones tentativas a una problemática utilizando un framework del lado del servidor.

## Criterios de evaluación asociados

- **2.1.1** Configura la conexión a una base de datos, según requerimiento.
- **2.1.2** Utiliza el administrador de Django, de acuerdo con los requerimientos.
- **2.1.3** Codifica funciones que realicen operaciones CRUD sobre una base de datos, según requerimiento.
- **2.1.4** Codifica una aplicación back end con acceso a base de datos y seguridad, de acuerdo con lo requerido por el problema planteado.

## Objetivo de la actividad

Integrar en una aplicación Django funcional los contenidos desarrollados hasta la Clase 8 de la Unidad 2, demostrando dominio de estructura de proyecto, persistencia, autenticación, autorización, CRUD, sesiones, manejo de archivos, validaciones, borrado lógico y despliegue. Se incorpora además un desafío de investigación autónoma para exportar información a Excel.

---

## Requerimientos técnicos y funcionales

### 1. Modelo de datos, Django Admin y nomenclatura

- Mínimo 6 tablas maestras y 4 tablas operacionales propias de la problemática. Las tablas internas de Django no cuentan dentro de este mínimo.
- Los nombres técnicos de modelos, tablas y campos deberán estar en inglés y seguir una convención consistente.
- Las relaciones deberán implementarse correctamente mediante `ForeignKey`, `OneToOneField` o `ManyToManyField` cuando corresponda.
- Los modelos principales deberán estar registrados y ser administrables desde Django Admin con una configuración coherente al proyecto.

### 2. Base de datos y borrado lógico

- La conexión debe configurarse mediante variables de entorno y migraciones reproducibles.
- Las entidades de negocio eliminables deberán utilizar `deleted_at` o un mecanismo equivalente de borrado lógico.
- Los listados y consultas normales no deben mostrar registros eliminados lógicamente; no se admite eliminación física como flujo normal de las entidades evaluadas.

### 3. Carga de datos para pruebas

- El proyecto deberá contener al menos 1.000 registros de negocio distribuidos de forma coherente para probar relaciones, permisos y paginación.
- La carga debe ser reproducible mediante management command, fixture o script de seed documentado en `README.md`.

### 4. Autenticación y recuperación de contraseña

- Implementar login y logout utilizando el sistema de autenticación de Django.
- Implementar recuperación de contraseña mediante código numérico de 6 dígitos. El flujo debe ser demostrable y el código no puede reutilizarse luego de una recuperación exitosa.
- La nueva contraseña se solicita dos veces y debe cumplir: mínimo 10 caracteres, mayúscula, minúscula, número y carácter especial. No se almacenan contraseñas en texto plano.

### 5. Usuarios, roles, permisos y scoping

- Crear al menos 3 usuarios de prueba con permisos diferentes y demostrables. Los roles pueden adaptarse a la problemática; por ejemplo, Administrador, Editor/Operador y Lector/Consulta.
- Las vistas deben protegerse mediante autenticación y permisos. Tener una sesión iniciada no implica autorización para todas las operaciones.
- Si la problemática maneja organización, sucursal, departamento, propietario u otro ámbito equivalente, los QuerySets deben respetar dicho scoping.

### 6. CRUD y validaciones

- Implementar al menos 4 CRUD completos sobre entidades relevantes: crear, listar/ver, actualizar y eliminar lógicamente.
- Utilizar `ModelForm` o una estructura Django equivalente, manteniendo la lógica organizada y evitando concentrar todo en una única vista.
- Aplicar validaciones del lado servidor para campos requeridos, rangos, duplicados y reglas propias del negocio.

### 7. Archivos e imágenes

- Al menos un CRUD deberá incorporar carga de imagen o archivo usando `multipart/form-data` y `request.FILES`.
- En imágenes se deberá validar tamaño, extensión permitida y contenido real mediante una técnica equivalente a `Pillow`/`Image.verify()`.
- `MEDIA_ROOT` y `MEDIA_URL` deben estar configurados correctamente y los archivos de usuario no deben versionarse en Git.

### 8. Paginación y sesiones

- Los listados operacionales deberán ofrecer al menos 5, 15 y 30 registros por página.
- La selección del tamaño debe mantenerse mediante `request.session` y el servidor debe rechazar o normalizar valores no permitidos.

### 9. SweetAlert2 y eliminación segura

- La acción eliminar debe solicitar confirmación con SweetAlert2.
- La eliminación se envía por POST con CSRF. Django debe verificar autenticación, permiso y scoping antes de ejecutar la acción.
- La confirmación visual no reemplaza la seguridad del servidor y el resultado debe ser borrado lógico, no eliminación física.

### 10. Investigación autónoma: exportación a Excel

- Investigar e implementar la descarga en formato `.xlsx` de al menos una tabla operacional del proyecto.
- El archivo debe contener encabezados y datos obtenidos desde la base de datos; no se acepta un Excel creado manualmente.
- La exportación debe respetar permisos, scoping y borrado lógico. El equipo podrá elegir la librería compatible con Django, pero deberá explicar su funcionamiento durante la defensa.

### 11. Repositorio y estructura del proyecto

- Proyecto modular con mínimo 2 aplicaciones internas y responsabilidades separadas.
- Después del primer push de inicialización, el trabajo debe realizarse en ramas y posteriormente integrarse. No se acepta desarrollo habitual directamente sobre `main`.
- El historial debe contener commits descriptivos. Deben incluirse `.gitignore`, `.env.example`, `requirements.txt` y `README.md`; `.env`, entornos virtuales y secretos quedan fuera del repositorio.

### 12. Despliegue en AWS Academy

- La aplicación deberá estar desplegada y operativa en AWS Academy al momento de la revisión.
- La demostración principal se realizará desde el despliegue y deberá permitir verificar login, permisos, paginación, CRUD, archivos, SweetAlert2, borrado lógico y Excel.

---

## Evidencias obligatorias

- URL del repositorio Git y hash del último commit integrado.
- URL pública de la aplicación desplegada en AWS Academy.
- `README.md` con instalación, variables de entorno, migraciones y comando/procedimiento de carga de datos.
- Tres usuarios de prueba con permisos distintos. Las contraseñas se entregan para la demostración y no se publican en el repositorio.
- Demostración reproducible de los 1.000 registros y de todas las funcionalidades solicitadas.

## Regla de defensa y autoría

> El docente podrá seleccionar a uno o más integrantes y preguntar por cualquier implementación presentada. El estudiante deberá identificar dónde se encuentra el código, explicar su propósito y describir su funcionamiento. Si no logra responder adecuadamente, el descuento se aplicará al criterio técnico relacionado con esa implementación.

### Criterio de revisión oral

_La comprensión del código se verifica dentro del criterio técnico correspondiente. No existe un descuento general adicional por preguntas: la evidencia oral complementa la demostración funcional._

---

## Rúbrica / Escala de apreciación formativa

**Puntaje referencial: 100 puntos** · El nivel de logro se utiliza para retroalimentación

| Criterio | Destacado | Habilitado | En desarrollo | No logrado |
|---|---|---|---|---|
| **Modelo de datos, Admin y nomenclatura** (11 pts) | 6+4 tablas, relaciones correctas, inglés y Admin coherente. 11 pts | Cumple mínimo con detalles menores. 7 pts | Faltan tablas o hay problemas relevantes. 3 pts | No presenta modelo mínimo funcional. 0 pts |
| **Estructura y Git** (9 pts) | Proyecto modular, ramas, commits, README y archivos de configuración correctos. 9 pts | Correcto con uno o dos ajustes menores. 6 pts | Estructura/ramas/configuración incompletas. 3 pts | Repositorio no reproducible o expone secretos. 0 pts |
| **Autenticación y recuperación** (9 pts) | Login/logout y código de 6 dígitos funcionan de extremo a extremo. 9 pts | Funcional con ajuste menor. 6 pts | Recuperación parcial o débil. 3 pts | No demuestra flujo funcional. 0 pts |
| **Seguridad de contraseña** (7 pts) | Confirma y valida longitud/complejidad usando mecanismos seguros de Django. 7 pts | Validaciones principales con detalle menor. 4 pts | Validación débil o incompleta. 2 pts | Manejo inseguro o sin validación. 0 pts |
| **Usuarios, permisos y scoping** (10 pts) | 3 usuarios diferenciados; permisos y scoping se demuestran correctamente. 10 pts | Funciona con restricción menor pendiente. 6 pts | Permisos parciales o solo en algunas vistas. 3 pts | Expone acciones/datos indebidos. 0 pts |
| **CRUD y validaciones** (11 pts) | 2 CRUD completos y validaciones de servidor coherentes. 11 pts | CRUD funcional con ajustes menores. 7 pts | CRUD incompleto o validación insuficiente. 3 pts | No demuestra CRUD funcional. 0 pts |
| **Archivos e imágenes** (8 pts) | Carga correcta y valida tamaño, extensión y contenido real. 8 pts | Funcional con una validación menor pendiente. 5 pts | Carga parcial o validaciones insuficientes. 2 pts | No implementa carga funcional. 0 pts |
| **SweetAlert2 + soft delete** (9 pts) | SweetAlert2 + POST/CSRF + permiso/scoping + borrado lógico. 9 pts | Flujo funcional con ajuste menor. 6 pts | Alerta funciona, pero seguridad o soft delete es parcial. 3 pts | Eliminación insegura/física o no funciona. 0 pts |
| **Paginación y sesión** (6 pts) | 5/15/30 y persistencia correcta en request.session. 6 pts | Paginación correcta con persistencia parcial. 4 pts | Paginación básica sin sesión o con errores. 2 pts | No implementa paginación funcional. 0 pts |
| **Investigación: Excel** (6 pts) | .xlsx real con encabezados/datos y respeta permisos, scoping y soft delete. 6 pts | Funcional con ajuste menor. 4 pts | Archivo parcial o alcance de datos incorrecto. 2 pts | No implementa exportación. 0 pts |
| **Carga de 1.000 datos** (6 pts) | >=1.000 datos y carga reproducible por seed/fixture/command. 6 pts | Cumple volumen con ajuste menor de reproducción. 4 pts | Volumen insuficiente o carga poco reproducible. 2 pts | No presenta datos suficientes. 0 pts |
| **Despliegue AWS Academy** (8 pts) | Operativo y permite demostrar todas las funciones solicitadas. 8 pts | Funcional con limitación menor. 5 pts | Parcial/inestable; depende de local. 2 pts | No existe despliegue operativo. 0 pts |

**Suma de puntajes máximos:** 11+9+9+7+10+11+8+9+6+6+6+8 = **100 pts**
