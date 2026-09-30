"""
Validadores de archivos para Evidence (Fase 8, Paso 8.1/8.2).

Evidence.file acepta imágenes Y PDF (Paso 8.1) porque el seed curado ya
usa PDF como evidencia. Cada formato necesita su propia verificación de
CONTENIDO real, no solo de extensión:
- Imágenes: Image.verify() de Pillow abre los bytes y confirma que son
  una imagen válida, no corrupta.
- PDF: Pillow no lee PDF. Se verifica la cabecera real del archivo (un
  PDF válido siempre empieza con los bytes "%PDF-").

Ambas evitan el caso "renombré archivo.exe a foto.jpg" -- el nombre no
protege nada, el contenido sí.
"""
import os

from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_PDF_EXTENSIONS = {'.pdf'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_PDF_EXTENSIONS
PDF_MAGIC_BYTES = b'%PDF-'


def validate_evidence_file(uploaded_file):
    """
    Validador de campo para Evidence.file. Se pasa como
    validators=[validate_evidence_file] en el propio FileField, para que
    la regla se cumpla sin importar desde dónde se suba el archivo (Admin
    hoy, formularios web en Fase 6, API a futuro) -- mismo criterio que
    Actividad.clean() de la evaluación anterior: la regla vive en el
    modelo, no en una pantalla puntual.
    """
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise ValidationError(
            f"El archivo pesa {filesizeformat(uploaded_file.size)}; "
            f"el máximo permitido es {filesizeformat(MAX_UPLOAD_SIZE)}."
        )

    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'Formato "{extension}" no permitido. Formatos válidos: '
            f"{', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    uploaded_file.seek(0)
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        _validate_image_content(uploaded_file)
    else:
        _validate_pdf_content(uploaded_file)
    uploaded_file.seek(0)  # deja el puntero al inicio para que Django lo guarde bien


def _validate_image_content(uploaded_file):
    try:
        Image.open(uploaded_file).verify()
    except (UnidentifiedImageError, OSError):
        raise ValidationError(
            "El archivo tiene extensión de imagen, pero su contenido no "
            "es una imagen válida (o está corrupto)."
        )


def _validate_pdf_content(uploaded_file):
    header = uploaded_file.read(len(PDF_MAGIC_BYTES))
    if header != PDF_MAGIC_BYTES:
        raise ValidationError(
            "El archivo tiene extensión .pdf, pero su contenido no "
            "corresponde a un PDF real."
        )