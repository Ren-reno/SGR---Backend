# SGR — Sistema de Gestión de Resultados (Backend Django)

Proyecto de Evaluación Sumativa II — Programación Back End (TI3041).
Caso: Delegaciones municipales, I. Municipalidad de La Serena.

## Requisitos previos
- Python 3.10+ (probado con 3.12)
- Git

No se requiere instalar un motor de base de datos aparte: el proyecto usa SQLite, incluido con Python.

## Instalación
```powershell
git clone <url-del-repo>
cd <carpeta-del-repo>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Variables de entorno
```powershell
copy .env.example .env
```
Completar `.env` con valores reales. Generar una `SECRET_KEY` nueva con:
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `True` en desarrollo |
| `DB_ENGINE` | `django.db.backends.sqlite3` |
| `DB_NAME` | Nombre del archivo de base de datos (`db.sqlite3`) |

## Base de datos
El archivo `db.sqlite3` se genera automáticamente al correr las migraciones — no requiere creación previa.

## Migraciones
```powershell
python manage.py migrate
```

## Carga de datos de prueba
_(se completa en la Fase 3 del proyecto)_

## Levantar el servidor
```powershell
python manage.py runserver
```

## Cuentas de prueba
_(se completa en la Fase 3, junto con el seed de datos — Decisión 5 de `decisiones.md`)_

## Documentación del proyecto

Documentación interna del equipo, en `docs/`:

| Documento | Contenido |
|---|---|
| `docs/decisiones.md` | Decisiones de diseño y alcance de esta entrega (7 entidades), con alternativas descartadas y su justificación |
| `docs/Plan_Proyecto_SGR_Fusionado.md` | Plan de trabajo por fases y reparto real del equipo |
| `docs/Guia_Proyecto_Software_SGR_Alumnos.md` | Documento fuente completo del caso SGR (MVP completo, 23 HU). No describe el alcance de este repo — se incluye por trazabilidad. Para el alcance real de esta entrega, ver `decisiones.md` |
| `docs/enunciado.md` | Enunciado completo de la Evaluación Sumativa II (rúbrica, criterios y requerimientos de las 100 pts) — la Fase 1 de este repo cubre el criterio "Conexión BD + Migraciones" (9 pts) |