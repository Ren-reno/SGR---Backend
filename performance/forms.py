"""ModelForms del CRUD web (Fase 6). Un formulario por entidad; 6.1 agrega
`ActivityForm`, 6.2 `EvidenceForm`, 6.3 `ValidationForm` y 6.4 `CommitmentForm`,
todos en este mismo archivo.

Las validaciones de servidor viven acá y en el `clean()` del modelo, no en el
template ni en JavaScript: lo que el navegador valide es comodidad, lo que
importa es lo que el servidor rechaza.
"""
import re

from django import forms
from django.utils import timezone

from organization.models import Delegation, Employee
from .models import Activity, CatalogItem, Commitment, Evidence, Meta, Validation
from .scoping import scope_delegations_for_user, scope_queryset_for_user

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
            # `localdate()` sigue `settings.TIME_ZONE` ('America/Santiago',
            # Decisión 27): es la fecha de hoy de quien usa el sistema.
            if date > timezone.localdate():
                self.add_error('date', 'La fecha de la evidencia no puede ser futura.')
            elif activity and date < activity.date:
                self.add_error(
                    'date',
                    'La fecha de la evidencia no puede ser anterior a la de '
                    f'su actividad ({activity.date:%d/%m/%Y}).',
                )
        return cleaned


# --- Paso 6.3: Validation --------------------------------------------------
# Valores de `Validation.decision`. La Guía (HU-11 / RF-013) dice que el
# verificador "puede aprobarla, rechazarla o solicitar corrección". 'Aprobada'
# es el valor que ya escriben el seed y la acción masiva del Admin; los otros
# dos son la redacción elegida acá (supuesto a confirmar, ver Decisión 24).
# `decision` sigue siendo texto libre en el modelo, así que las opciones viven
# en el formulario y no exigen migración.
DECISION_APPROVED = 'Aprobada'
DECISION_REJECTED = 'Rechazada'
DECISION_CORRECTION = 'Corrección solicitada'
DECISION_CHOICES = (
    (DECISION_APPROVED, DECISION_APPROVED),
    (DECISION_REJECTED, DECISION_REJECTED),
    (DECISION_CORRECTION, DECISION_CORRECTION),
)

# Grupo que ya usa ValidationAdmin.formfield_for_foreignkey para el desplegable
# `employee`: solo un Employee cuyo usuario es Verificador puede figurar como
# quien emitió la revisión.
VERIFIER_GROUP = 'Verificador'


class ValidationForm(forms.ModelForm):
    """Alta y edición de `Validation` (paso 6.3).

    Reproduce lo que ya hace `ValidationAdmin` y lo lleva a la web:

    - `evidence` y `employee` se acotan con `scope_queryset_for_user` (el
      scoping de la vista solo acota lo que se ve, no lo que se escribe).
    - `evidence` solo ofrece evidencias SIN validación. `Validation.evidence`
      es OneToOne (0..1) y la Decisión 9 descartó re-aprobar creando otra
      fila; una validación eliminada lógicamente también sigue ocupando el
      lugar (`validation__isnull` mira la tabla completa, no el manager). Al
      editar, `evidence` queda de solo lectura: una revisión no se mueve a
      otra evidencia.
    - `result` no se pide: se deriva de `decision` (RN-009: solo una
      validación aprobada aporta puntaje), así que nunca pueden contradecirse.
    - `version` no se edita: su semántica no está confirmada (Decisión 24).
    """

    decision = forms.ChoiceField(
        label='Decisión',
        choices=(('', 'Seleccione una decisión'),) + DECISION_CHOICES,
    )

    class Meta:
        model = Validation
        fields = ('evidence', 'employee', 'decision', 'date', 'notes')
        labels = {
            'evidence': 'Evidencia',
            'employee': 'Verificador',
            'date': 'Fecha de la revisión',
            'notes': 'Observación',
        }
        help_texts = {
            'date': 'No puede ser futura ni anterior a la fecha de la evidencia.',
            'notes': 'Obligatoria al rechazar o solicitar corrección.',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        editing = bool(self.instance.pk)

        if editing:
            # Solo su propia evidencia, para que el campo deshabilitado siga
            # validando contra su queryset.
            evidence_qs = Evidence.objects.filter(pk=self.instance.evidence_id)
        else:
            evidence_qs = Evidence.objects.filter(validation__isnull=True)
        evidence = self.fields['evidence']
        evidence.queryset = scope_queryset_for_user(
            evidence_qs, user, delegation_lookup='activity__employee__',
        ).select_related('activity__employee').order_by('-date', 'code')
        evidence.label_from_instance = lambda obj: (
            f'{obj.code} · {obj.date:%d/%m/%Y} · {obj.activity.employee.name}'
        )
        evidence.error_messages['invalid_choice'] = (
            'Esta evidencia no está disponible: ya tiene una validación o '
            'no pertenece a su Delegación.'
        )
        if editing:
            evidence.disabled = True
            evidence.help_text = (
                'La evidencia no se puede cambiar una vez validada.'
            )

        employee = self.fields['employee']
        employee.queryset = scope_queryset_for_user(
            Employee.objects.filter(user__groups__name=VERIFIER_GROUP).distinct(),
            user, delegation_lookup='',
        ).order_by('name')
        employee.error_messages['invalid_choice'] = (
            'Seleccione un verificador de la lista.'
        )

        self.fields['date'].widget.attrs['max'] = timezone.localdate().isoformat()

        if not editing:
            # Comodidad: quien revisa suele ser quien registra, y la fecha
            # habitual es hoy. Solo son valores iniciales; el servidor valida
            # lo que llegue.
            own = employee.queryset.filter(user=user).first()
            if own is not None:
                self.initial.setdefault('employee', own.pk)
            self.initial.setdefault('date', timezone.localdate())

    def clean_evidence(self):
        evidence = self.cleaned_data['evidence']
        # Mismo criterio que la Decisión 9(b) para la acción masiva: no se
        # revisa una evidencia sin archivo. Solo al crear; una revisión ya
        # emitida se puede editar aunque el archivo se haya quitado después.
        if not self.instance.pk and not evidence.file:
            raise forms.ValidationError(
                'La evidencia no tiene archivo cargado; no se puede validar.'
            )
        return evidence

    def clean_notes(self):
        return self.cleaned_data['notes'].strip()

    def clean(self):
        cleaned = super().clean()
        decision = cleaned.get('decision')
        date = cleaned.get('date')
        evidence = cleaned.get('evidence')

        if decision:
            # RN-009: solo una validación aprobada aporta puntaje.
            self.instance.result = decision == DECISION_APPROVED
            # CA-02 / HU-11: el rechazo conserva y muestra el motivo; pedir
            # una corrección sin decir cuál no le sirve a quien la recibe.
            if decision != DECISION_APPROVED and not cleaned.get('notes'):
                self.add_error(
                    'notes',
                    'La observación es obligatoria al rechazar o solicitar '
                    'corrección.',
                )

        if date:
            if date > timezone.localdate():
                self.add_error('date', 'La fecha de la revisión no puede ser futura.')
            elif evidence and date < evidence.date:
                self.add_error(
                    'date',
                    'La revisión no puede ser anterior a la fecha de la '
                    f'evidencia ({evidence.date:%d/%m/%Y}).',
                )
        return cleaned


class CommitmentForm(forms.ModelForm):
    """Alta y edición de `Commitment` (paso 6.4).

    Recibe `user` (lo pasa la vista) para acotar los DOS desplegables que
    determinan el ámbito del compromiso, igual que hace
    `CommitmentAdmin.formfield_for_foreignkey`:

    - `delegation`: solo la Delegación del usuario (`scope_delegations_for_user`;
      `scope_queryset_for_user` no sirve acá porque `Delegation` no tiene
      campo `delegation_id`).
    - `responsible`: solo empleados de esa misma Delegación.

    Sin esto, quien puede crear o editar compromisos de su Delegación podía
    reasignarlos a otra cambiando el valor en el POST: la vista acota QUÉ
    registros se ven, no QUÉ valores se escriben. Que `responsible` pertenezca
    a `delegation` lo exige `Commitment.clean()` (Decisión 17), que
    `ModelForm` ejecuta solo; acá no se reescribe.
    """

    class Meta:
        model = Commitment
        fields = (
            'delegation', 'responsible', 'origin', 'requester', 'territory',
            'due_date', 'support_area', 'status', 'observation',
        )
        labels = {
            'delegation': 'Delegación',
            'responsible': 'Responsable',
            'origin': 'Origen',
            'requester': 'Solicitante',
            'territory': 'Territorio',
            'due_date': 'Fecha comprometida',
            'support_area': 'Área de apoyo',
            'status': 'Estado',
            'observation': 'Observación',
        }
        help_texts = {
            'delegation': 'Debe ser la Delegación del responsable.',
            'due_date': 'No puede ser anterior a hoy (al registrar o al cambiarla).',
        }
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observation': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        delegations = scope_delegations_for_user(
            Delegation.objects.all(), user,
        ).order_by('name')
        self.fields['delegation'].queryset = delegations
        self.fields['responsible'].queryset = scope_queryset_for_user(
            Employee.objects.all(), user, delegation_lookup='',
        ).order_by('name')
        # Alta con una sola Delegación posible (el caso de todo usuario que
        # no es superuser): queda preseleccionada. `self.initial` ya trae la
        # clave `delegation` en None en un formulario nuevo, por eso no se
        # pregunta "si no está", sino "si está vacía".
        if not self.instance.pk and self.initial.get('delegation') is None:
            only = list(delegations[:2])
            if len(only) == 1:
                self.initial['delegation'] = only[0].pk

    def clean_due_date(self):
        due_date = self.cleaned_data['due_date']
        # RF-016: compromisos FUTUROS. Solo se exige al registrar o cuando la
        # fecha cambia: un compromiso vencido tiene que seguir siendo
        # editable (p. ej. pasarlo a "Realizado") sin tocar su fecha.
        # `localdate()` sigue `settings.TIME_ZONE` ('America/Santiago', Decisión 27).
        creating = self.instance.pk is None
        if (creating or 'due_date' in self.changed_data) \
                and due_date < timezone.localdate():
            raise forms.ValidationError(
                'La fecha comprometida no puede ser anterior a hoy.'
            )
        return due_date

    def clean(self):
        cleaned = super().clean()
        responsible = cleaned.get('responsible')
        due_date = cleaned.get('due_date')
        origin = cleaned.get('origin')
        requester = cleaned.get('requester')
        territory = cleaned.get('territory')
        if responsible and due_date and origin and requester and territory:
            # Duplicado: mismo responsable, fecha, origen, solicitante y
            # territorio. Protege del doble clic en "Guardar" y de
            # re-ingresar lo ya registrado. `objects` excluye los eliminados
            # lógicamente (Decisión 20), y en edición se excluye la propia
            # fila. `iexact` en SQLite ignora mayúsculas solo en ASCII
            # ('PÉREZ' no coincide con 'Pérez'), igual que en ActivityForm.
            duplicates = Commitment.objects.filter(
                responsible=responsible, due_date=due_date,
                origin__iexact=origin, requester__iexact=requester,
                territory__iexact=territory,
            ).exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError(
                    'Ya existe un compromiso con el mismo responsable, '
                    'fecha, origen, solicitante y territorio.'
                )
        return cleaned
