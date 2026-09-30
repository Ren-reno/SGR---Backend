"""ModelForms del CRUD web (Fase 6). Un formulario por entidad; 6.1 agrega
`ActivityForm`, 6.2 `EvidenceForm`, y 6.3 y 6.4 agregan los suyos a este mismo
archivo.

Las validaciones de servidor viven acá y en el `clean()` del modelo, no en el
template ni en JavaScript: lo que el navegador valide es comodidad, lo que
importa es lo que el servidor rechaza.
"""
import re

from django import forms
from django.utils import timezone

from organization.models import Employee
from .models import Activity, CatalogItem, Evidence, Meta
from .scoping import scope_queryset_for_user

# Solo dígitos y los separadores habituales de un teléfono; al menos 7
# dígitos (evita "1" o "abc" en un campo opcional que, si se llena, debe
# servir para llamar).
_PHONE_CHARS = re.compile(r'^[0-9+()\-\s]+$')
_MIN_PHONE_DIGITS = 7


class ActivityForm(forms.ModelForm):
    """Alta y edición de `Activity` (paso 6.1).

    Recibe `user` (lo pasa la vista) para acotar el desplegable `employee` a
    la Delegación de quien edita. Sin esto, un Funcionario con permiso de
    edición podía reasignar una actividad a un empleado de otra Delegación
    cambiando el valor en el POST: la vista solo acota QUÉ registros ve, no
    QUÉ valores puede escribir. Las reglas de negocio del modelo (fecha
    dentro del `Period`) las aplica `Model.clean()`, que ModelForm ejecuta
    solo; acá no se reescriben.
    """

    class Meta:
        model = Activity
        fields = (
            'employee', 'period', 'meta', 'activity_type', 'service',
            'attention', 'sub_attention', 'date', 'request_description',
            'action_taken', 'contact_name', 'contact_phone', 'status',
        )
        labels = {
            'employee': 'Funcionario',
            'period': 'Período',
            'meta': 'Meta',
            'activity_type': 'Tipo de actividad',
            'service': 'Servicio',
            'attention': 'Tipo de atención',
            'sub_attention': 'Sub atención',
            'date': 'Fecha',
            'request_description': 'Solicitud / problema',
            'action_taken': 'Acción realizada',
            'contact_name': 'Nombre de contacto',
            'contact_phone': 'Teléfono de contacto',
            'status': 'Estado',
        }
        help_texts = {
            'meta': 'Opcional: una actividad aporta a una sola meta.',
            'date': 'Debe caer dentro del período elegido.',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'request_description': forms.Textarea(attrs={'rows': 3}),
            'action_taken': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['employee'].queryset = scope_queryset_for_user(
            Employee.objects.all(), user, delegation_lookup='',
        ).order_by('name')
        self.fields['meta'].queryset = Meta.objects.select_related(
            'position', 'period'
        ).order_by('item_name')
        # Solo catálogos vigentes; si la actividad ya tenía uno dado de baja,
        # se conserva en el desplegable para poder editarla sin perderlo.
        attention_qs = CatalogItem.objects.filter(
            category=CatalogItem.CATEGORY_ATTENTION
        )
        active = attention_qs.filter(is_active=True)
        if self.instance.pk and self.instance.attention_id:
            active = active | attention_qs.filter(pk=self.instance.attention_id)
        self.fields['attention'].queryset = active.distinct().order_by('name')

    def clean_contact_phone(self):
        phone = self.cleaned_data['contact_phone'].strip()
        if not phone:
            return phone
        digits = sum(ch.isdigit() for ch in phone)
        if not _PHONE_CHARS.match(phone) or digits < _MIN_PHONE_DIGITS:
            raise forms.ValidationError(
                'Ingrese un teléfono válido (solo dígitos, espacios, +, -, '
                f'paréntesis; al menos {_MIN_PHONE_DIGITS} dígitos).'
            )
        return phone

    def clean(self):
        cleaned = super().clean()
        employee = cleaned.get('employee')
        date = cleaned.get('date')
        description = (cleaned.get('request_description') or '').strip()
        activity_type = cleaned.get('activity_type')
        if employee and date and activity_type and description:
            # Duplicado: misma persona, día, tipo y solicitud. Protege del
            # doble clic en "Guardar" y de re-ingresar lo ya registrado.
            # `objects` excluye los eliminados lógicamente (Decisión 20), y
            # en edición se excluye la propia fila.
            duplicates = Activity.objects.filter(
                employee=employee, date=date, activity_type=activity_type,
                request_description__iexact=description,
            ).exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError(
                    'Ya existe una actividad con el mismo funcionario, '
                    'fecha, tipo y solicitud.'
                )
        return cleaned


# RF-011: el código de evidencia debe servir "para nombrar y vincular" el
# archivo, así que se limita a letras, dígitos, guion y guion bajo (sin
# espacios ni "/"). Solo se exige al crear; ver EvidenceForm.clean_code().
_EVIDENCE_CODE_CHARS = re.compile(r'^[A-Za-z0-9_-]+$')


def _activity_label(activity):
    """Texto del desplegable `activity`: `Activity.__str__` solo trae el id y
    el tipo, insuficiente para distinguir dos actividades al elegir una."""
    return (
        f'#{activity.pk} · {activity.date:%d/%m/%Y} · '
        f'{activity.employee} · {activity.activity_type}'
    )


class EvidenceForm(forms.ModelForm):
    """Alta y edición de `Evidence` (paso 6.2).

    Igual que `ActivityForm`, recibe `user` para acotar el desplegable
    `activity` a la Delegación de quien escribe: sin eso, quien puede editar
    una evidencia podría colgarla de una actividad ajena cambiando el valor
    en el POST (la vista solo acota qué registros ve, no qué valores escribe).

    Lo que este formulario decide distinto al de Activity, por cómo es el
    modelo:

    - `code` es la clave primaria y es inmutable (RN-010). Al editar queda
      `disabled`: Django ignora lo que llegue por POST para ese campo. Sin
      eso, cambiar el código en el POST haría que `save()` insertara una fila
      nueva y dejara la original intacta.
    - `review_status` NO está en el formulario. Es el resultado del flujo de
      validación (Decisión 9-bis: lo actualiza quien valida, no quien carga),
      y dejarlo editable permitiría a un Funcionario marcar su propia
      evidencia como "Aprobada" (RN-009). Al crear toma el default del modelo.
    - El archivo se exige al crear; al editar, si no se sube otro, se conserva
      el actual. Tamaño, extensión y contenido real del archivo NO se validan
      aquí: eso es la Fase 8.
    """

    class Meta:
        model = Evidence
        fields = ('code', 'activity', 'file', 'date', 'metadata')
        labels = {
            'code': 'Código',
            'activity': 'Actividad',
            'file': 'Archivo',
            'date': 'Fecha',
            'metadata': 'Metadatos',
        }
        help_texts = {
            'code': 'Único e inmutable. Solo letras, dígitos, guion y guion bajo.',
            'date': 'No puede ser futura ni anterior a la fecha de la actividad.',
            'metadata': 'Opcional: descripción del archivo, cámara, lugar, etc.',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'metadata': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['activity'].queryset = scope_queryset_for_user(
            Activity.objects.select_related('employee'), user,
            delegation_lookup='employee__',
        ).order_by('-date', '-pk')
        self.fields['activity'].label_from_instance = _activity_label
        # Textos del widget de archivo en español (los de Django salen en
        # inglés porque LANGUAGE_CODE es en-us).
        self.fields['file'].widget.initial_text = 'Archivo actual'
        self.fields['file'].widget.input_text = 'Reemplazar por'
        if not self.instance._state.adding:
            self.fields['code'].disabled = True
            self.fields['code'].help_text = (
                'El código no se puede cambiar una vez creada la evidencia.'
            )

    def clean_code(self):
        if not self.instance._state.adding:
            # Campo deshabilitado: el valor es el de la fila, no uno escrito.
            # No se le re-aplica el formato, para que una evidencia antigua
            # con un código "raro" (creada desde el Admin) siga editable.
            return self.instance.pk
        code = self.cleaned_data['code']
        if not _EVIDENCE_CODE_CHARS.match(code):
            raise forms.ValidationError(
                'Use solo letras, dígitos, guion (-) y guion bajo (_), '
                'sin espacios.'
            )
        # `all_objects`, no `objects`: una evidencia eliminada lógicamente
        # sigue ocupando la clave primaria (Decisión 20), así que su código
        # tampoco se puede reutilizar. `iexact` evita "EVID-001" y "evid-001"
        # como dos evidencias distintas.
        clash = Evidence.all_objects.filter(code__iexact=code).first()
        if clash is not None:
            if clash.deleted_at is not None:
                raise forms.ValidationError(
                    'Ese código perteneció a una evidencia eliminada y no '
                    'se puede reutilizar.'
                )
            raise forms.ValidationError('Ya existe una evidencia con ese código.')
        return code

    def clean(self):
        cleaned = super().clean()
        activity = cleaned.get('activity')
        date = cleaned.get('date')
        if date:
            # `localdate()` usa TIME_ZONE (UTC): Chile va por detrás de UTC,
            # así que la fecha local de un usuario nunca supera a esta.
            if date > timezone.localdate():
                self.add_error('date', 'La fecha de la evidencia no puede ser futura.')
            elif activity and date < activity.date:
                self.add_error(
                    'date',
                    'La fecha de la evidencia no puede ser anterior a la de '
                    f'su actividad ({activity.date:%d/%m/%Y}).',
                )
        return cleaned
