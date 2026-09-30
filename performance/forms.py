"""ModelForms del CRUD web (Fase 6). Un formulario por entidad; 6.1 agrega
`ActivityForm`, y 6.2 a 6.4 agregan los suyos a este mismo archivo.

Las validaciones de servidor viven acá y en el `clean()` del modelo, no en el
template ni en JavaScript: lo que el navegador valide es comodidad, lo que
importa es lo que el servidor rechaza.
"""
import re

from django import forms

from organization.models import Employee
from .models import Activity, CatalogItem, Meta
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
