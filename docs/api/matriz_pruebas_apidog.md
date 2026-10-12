# Matriz de pruebas en Apidog (API REST SGR, Evaluación Sumativa 3)

Plantilla para registrar la ejecución de la colección `docs/api/sgr_api.postman_collection.json`. Cada integrante la completa en su propio equipo.

## Reglas para completarla

- Las columnas **Estado observado** y **Respuesta representativa** se dejan vacías en el repositorio: las llena cada integrante con lo que ve al ejecutar.
- Usa solo datos ficticios.
- **Oculta** `access`, `refresh` y contraseñas en capturas y respuestas (reemplázalos por `***`).
- No subas a Git contraseñas, tokens ni la colección exportada tras ejecutarla sin revisarla.

## Preparación (Apidog)

1. Levanta el servidor local y carga los datos: `python manage.py runserver` y `python manage.py load_api_demo_data --password TU_CLAVE_LOCAL`.
2. Importa `docs/api/sgr_api.postman_collection.json` (importación de colección Postman v2.1; verifica en tu versión de Apidog que los scripts de las pestañas de pruebas se conserven).
3. Crea un **entorno local** y selecciónalo. Variables a completar solo en ese entorno:

| Variable | Valor |
|---|---|
| `base_url` | `http://127.0.0.1:8000` |
| `username` / `password` | usuario `api_admin` y su clave (se entrega aparte) |
| `username_operador` / `password_operador` | usuario `api_operador` y su clave |
| `username_sinrol` / `password_sinrol` | usuario `api_sinrol` y su clave |

   Las variables `access`, `refresh`, `access_operador`, `access_sinrol` y las que empiezan con `ref_` o `new_` se llenan solas con los scripts de la carpeta 0 y de cada petición. Si tu Apidog no ejecuta los scripts, cópialas a mano desde la respuesta correspondiente.
4. Ejecuta las carpetas en orden (0 a 7). La carpeta 0 debe correr primero.

## Resumen: las 8 comprobaciones de la rúbrica

| Comprobación | Solicitud o alcance | Identidad | Estado esperado | Carpeta de la colección | Estado observado | Respuesta representativa |
|---|---|---|---|---|---|---|
| Cobertura de modelos | CRUD de las cuatro entidades principales; GET lista y detalle de las dos operacionales | Administrador / operador | 200, 201, 204 según método | 1 y 5 (y 3 para operador) |  |  |
| JWT | Obtener token y renovar access | Administrador | 200 | 0 |  |  |
| Sin autenticación | GET de recurso protegido | Sin token | 401 | 2 |  |  |
| Solo lectura | GET y POST de una principal | Operador | 200 y 403 | 3 |  |  |
| Sin rol API | GET de recurso protegido | Tercer usuario | 403 | 4 |  |  |
| CRUD completo | POST, GET detalle, PATCH o PUT, DELETE | Administrador | 201, 200, 200, 204 (borrado lógico: el registro deja de figurar, 404) | 5 |  |  |
| Errores | Dos validaciones e id inexistente | Administrador | 400, 400, 404 | 6 |  |  |
| Paginación | GET de dos páginas de recurso voluminoso | Operador | 200 y resultados distintos | 7 |  |  |

## Detalle: todas las peticiones de la colección

| # | Carpeta | Petición | Método | URL | Identidad | Estado esperado | Estado observado | Respuesta representativa (JWT y contraseñas ocultos) |
|---|---|---|---|---|---|---|---|---|
| 1 | 0. JWT y datos de referencia | Token (administrador) | POST | `{{base_url}}/api/token/` | Credenciales de api_admin | 200 |  |  |
| 2 | 0. JWT y datos de referencia | Renovar access (administrador) | POST | `{{base_url}}/api/token/refresh/` | Refresh token de api_admin | 200 |  |  |
| 3 | 0. JWT y datos de referencia | Token (operador) | POST | `{{base_url}}/api/token/` | Credenciales de api_operador | 200 |  |  |
| 4 | 0. JWT y datos de referencia | Token (sin rol API) | POST | `{{base_url}}/api/token/` | Credenciales de api_sinrol | 200 |  |  |
| 5 | 0. JWT y datos de referencia | Referencia: una actividad | GET | `{{base_url}}/api/activities/?page_size=1` | Administrador (api_admin) | 200 |  |  |
| 6 | 0. JWT y datos de referencia | Referencia: un compromiso | GET | `{{base_url}}/api/commitments/?page_size=1` | Administrador (api_admin) | 200 |  |  |
| 7 | 0. JWT y datos de referencia | Referencia: una meta | GET | `{{base_url}}/api/metas/?page_size=1` | Administrador (api_admin) | 200 |  |  |
| 8 | 0. JWT y datos de referencia | Referencia: una evidencia | GET | `{{base_url}}/api/evidence/?page_size=1` | Administrador (api_admin) | 200 |  |  |
| 9 | 0. JWT y datos de referencia | Referencia: una validacion | GET | `{{base_url}}/api/validations/?page_size=1` | Administrador (api_admin) | 200 |  |  |
| 10 | 1. Cobertura de modelos (administrador) | Lista de activities | GET | `{{base_url}}/api/activities/` | Administrador (api_admin) | 200 |  |  |
| 11 | 1. Cobertura de modelos (administrador) | Lista de commitments | GET | `{{base_url}}/api/commitments/` | Administrador (api_admin) | 200 |  |  |
| 12 | 1. Cobertura de modelos (administrador) | Lista de metas | GET | `{{base_url}}/api/metas/` | Administrador (api_admin) | 200 |  |  |
| 13 | 1. Cobertura de modelos (administrador) | Lista de periods | GET | `{{base_url}}/api/periods/` | Administrador (api_admin) | 200 |  |  |
| 14 | 1. Cobertura de modelos (administrador) | Lista de evidence | GET | `{{base_url}}/api/evidence/` | Administrador (api_admin) | 200 |  |  |
| 15 | 1. Cobertura de modelos (administrador) | Lista de validations | GET | `{{base_url}}/api/validations/` | Administrador (api_admin) | 200 |  |  |
| 16 | 1. Cobertura de modelos (administrador) | Detalle de evidence | GET | `{{base_url}}/api/evidence/{{ref_evidence_code}}/` | Administrador (api_admin) | 200 |  |  |
| 17 | 1. Cobertura de modelos (administrador) | Detalle de validations | GET | `{{base_url}}/api/validations/{{ref_validation_id}}/` | Administrador (api_admin) | 200 |  |  |
| 18 | 2. Sin autenticación (401) | Lista de activities sin token | GET | `{{base_url}}/api/activities/` | Sin token | 401 |  |  |
| 19 | 2. Sin autenticación (401) | Lista de commitments sin token | GET | `{{base_url}}/api/commitments/` | Sin token | 401 |  |  |
| 20 | 2. Sin autenticación (401) | Lista de metas sin token | GET | `{{base_url}}/api/metas/` | Sin token | 401 |  |  |
| 21 | 2. Sin autenticación (401) | Lista de periods sin token | GET | `{{base_url}}/api/periods/` | Sin token | 401 |  |  |
| 22 | 2. Sin autenticación (401) | Lista de evidence sin token | GET | `{{base_url}}/api/evidence/` | Sin token | 401 |  |  |
| 23 | 2. Sin autenticación (401) | Lista de validations sin token | GET | `{{base_url}}/api/validations/` | Sin token | 401 |  |  |
| 24 | 2. Sin autenticación (401) | Detalle de activities sin token | GET | `{{base_url}}/api/activities/{{ref_activity_id}}/` | Sin token | 401 |  |  |
| 25 | 3. Solo lectura (operador) | GET lista de activities | GET | `{{base_url}}/api/activities/` | Operador (api_operador) | 200 |  |  |
| 26 | 3. Solo lectura (operador) | POST en activities (bloqueado) | POST | `{{base_url}}/api/activities/` | Operador (api_operador) | 403 |  |  |
| 27 | 3. Solo lectura (operador) | GET lista de evidence | GET | `{{base_url}}/api/evidence/` | Operador (api_operador) | 200 |  |  |
| 28 | 3. Solo lectura (operador) | GET detalle de evidence | GET | `{{base_url}}/api/evidence/{{ref_evidence_code}}/` | Operador (api_operador) | 200 |  |  |
| 29 | 3. Solo lectura (operador) | GET lista de validations | GET | `{{base_url}}/api/validations/` | Operador (api_operador) | 200 |  |  |
| 30 | 3. Solo lectura (operador) | GET detalle de validations | GET | `{{base_url}}/api/validations/{{ref_validation_id}}/` | Operador (api_operador) | 200 |  |  |
| 31 | 4. Sin rol API (403) | Lista de activities sin rol | GET | `{{base_url}}/api/activities/` | Sin rol API (api_sinrol) | 403 |  |  |
| 32 | 4. Sin rol API (403) | Lista de commitments sin rol | GET | `{{base_url}}/api/commitments/` | Sin rol API (api_sinrol) | 403 |  |  |
| 33 | 4. Sin rol API (403) | Lista de metas sin rol | GET | `{{base_url}}/api/metas/` | Sin rol API (api_sinrol) | 403 |  |  |
| 34 | 4. Sin rol API (403) | Lista de periods sin rol | GET | `{{base_url}}/api/periods/` | Sin rol API (api_sinrol) | 403 |  |  |
| 35 | 4. Sin rol API (403) | Lista de evidence sin rol | GET | `{{base_url}}/api/evidence/` | Sin rol API (api_sinrol) | 403 |  |  |
| 36 | 4. Sin rol API (403) | Lista de validations sin rol | GET | `{{base_url}}/api/validations/` | Sin rol API (api_sinrol) | 403 |  |  |
| 37 | 5. CRUD completo (administrador) | Period: crear | POST | `{{base_url}}/api/periods/` | Administrador (api_admin) | 201 |  |  |
| 38 | 5. CRUD completo (administrador) | Period: detalle | GET | `{{base_url}}/api/periods/{{new_period_id}}/` | Administrador (api_admin) | 200 |  |  |
| 39 | 5. CRUD completo (administrador) | Period: actualizar (PATCH) | PATCH | `{{base_url}}/api/periods/{{new_period_id}}/` | Administrador (api_admin) | 200 |  |  |
| 40 | 5. CRUD completo (administrador) | Meta: crear | POST | `{{base_url}}/api/metas/` | Administrador (api_admin) | 201 |  |  |
| 41 | 5. CRUD completo (administrador) | Meta: detalle | GET | `{{base_url}}/api/metas/{{new_meta_id}}/` | Administrador (api_admin) | 200 |  |  |
| 42 | 5. CRUD completo (administrador) | Meta: actualizar (PATCH) | PATCH | `{{base_url}}/api/metas/{{new_meta_id}}/` | Administrador (api_admin) | 200 |  |  |
| 43 | 5. CRUD completo (administrador) | Meta: eliminar (borrado físico) | DELETE | `{{base_url}}/api/metas/{{new_meta_id}}/` | Administrador (api_admin) | 204 |  |  |
| 44 | 5. CRUD completo (administrador) | Meta: ya no existe | GET | `{{base_url}}/api/metas/{{new_meta_id}}/` | Administrador (api_admin) | 404 |  |  |
| 45 | 5. CRUD completo (administrador) | Commitment: crear | POST | `{{base_url}}/api/commitments/` | Administrador (api_admin) | 201 |  |  |
| 46 | 5. CRUD completo (administrador) | Commitment: detalle | GET | `{{base_url}}/api/commitments/{{new_commitment_id}}/` | Administrador (api_admin) | 200 |  |  |
| 47 | 5. CRUD completo (administrador) | Commitment: actualizar (PATCH) | PATCH | `{{base_url}}/api/commitments/{{new_commitment_id}}/` | Administrador (api_admin) | 200 |  |  |
| 48 | 5. CRUD completo (administrador) | Commitment: eliminar (borrado lógico) | DELETE | `{{base_url}}/api/commitments/{{new_commitment_id}}/` | Administrador (api_admin) | 204 |  |  |
| 49 | 5. CRUD completo (administrador) | Commitment: ya no figura | GET | `{{base_url}}/api/commitments/{{new_commitment_id}}/` | Administrador (api_admin) | 404 |  |  |
| 50 | 5. CRUD completo (administrador) | Activity: crear | POST | `{{base_url}}/api/activities/` | Administrador (api_admin) | 201 |  |  |
| 51 | 5. CRUD completo (administrador) | Activity: detalle | GET | `{{base_url}}/api/activities/{{new_activity_id}}/` | Administrador (api_admin) | 200 |  |  |
| 52 | 5. CRUD completo (administrador) | Activity: actualizar (PATCH) | PATCH | `{{base_url}}/api/activities/{{new_activity_id}}/` | Administrador (api_admin) | 200 |  |  |
| 53 | 5. CRUD completo (administrador) | Activity: eliminar (borrado lógico) | DELETE | `{{base_url}}/api/activities/{{new_activity_id}}/` | Administrador (api_admin) | 204 |  |  |
| 54 | 5. CRUD completo (administrador) | Activity: ya no figura | GET | `{{base_url}}/api/activities/{{new_activity_id}}/` | Administrador (api_admin) | 404 |  |  |
| 55 | 5. CRUD completo (administrador) | Period: eliminar (borrado físico) | DELETE | `{{base_url}}/api/periods/{{new_period_id}}/` | Administrador (api_admin) | 204 |  |  |
| 56 | 5. CRUD completo (administrador) | Period: ya no existe | GET | `{{base_url}}/api/periods/{{new_period_id}}/` | Administrador (api_admin) | 404 |  |  |
| 57 | 6. Errores (administrador) | 400 por regla: período con fechas invertidas | POST | `{{base_url}}/api/periods/` | Administrador (api_admin) | 400 |  |  |
| 58 | 6. Errores (administrador) | 400 por campo: compromiso sin origin | POST | `{{base_url}}/api/commitments/` | Administrador (api_admin) | 400 |  |  |
| 59 | 6. Errores (administrador) | 404: id inexistente | GET | `{{base_url}}/api/activities/999999999/` | Administrador (api_admin) | 404 |  |  |
| 60 | 6. Errores (administrador) | 409: período con referencias no se puede borrar | DELETE | `{{base_url}}/api/periods/{{ref_period}}/` | Administrador (api_admin) | 409 |  |  |
| 61 | 7. Paginación (operador) | Activities: página 1 | GET | `{{base_url}}/api/activities/?page=1` | Operador (api_operador) | 200 |  |  |
| 62 | 7. Paginación (operador) | Activities: página 2 | GET | `{{base_url}}/api/activities/?page=2` | Operador (api_operador) | 200 |  |  |

## Notas

- Estado `204` en `Commitment` y `Activity`: borrado lógico. La petición "ya no figura" (404) demuestra que el registro deja de aparecer en consultas normales.
- `Period` y `Meta` se borran físicamente (204). Un período con metas o actividades asociadas responde `409`.
- Las peticiones de la carpeta 5 crean y borran sus propios registros; no tocan los datos cargados.
