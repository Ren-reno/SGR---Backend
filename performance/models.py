import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import ProtectedError

from organization.models import Delegation, Employee, Position
from .soft_delete import SoftDeleteModel
from .validators import validate_evidence_file

class Period(models.Model):

    start_date = models.DateField()
    end_date = models.DateField()
    computable_days = models.PositiveIntegerField()
    status = models.CharField(max_length=30)
    amber_threshold = models.DecimalField(max_digits=5, decimal_places=2)
    collective_threshold = models.DecimalField(max_digits=5, decimal_places=2)
    parameters_version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Período {self.start_date} – {self.end_date}"


class CatalogItem(models.Model):

    CATEGORY_ATTENTION = 'attention'
    CATEGORY_CHOICES = [
        (CATEGORY_ATTENTION, 'Tipo Atención'),
    ]

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'name'], name='unique_catalog_item_per_category'
            )
        ]
        ordering = ('category', 'name')

    def __str__(self):
        return self.name


class Meta(models.Model):
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name='goals'
    )
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT, related_name='goals'
    )
    item_name = models.CharField(max_length=150)
    target_value = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    weight = models.DecimalField(max_digits=5, decimal_places=2)

    def clean(self):
        super().clean()
        errors = {}

        if self.target_value is not None and self.target_value <= 0:
            errors['target_value'] = (
                f"El valor objetivo ({self.target_value}) debe ser mayor "
                "que cero (RN-002)."
            )

        if self.position_id is not None and self.period_id is not None and self.weight is not None:
            other_weights = Meta.objects.filter(
                position_id=self.position_id, period_id=self.period_id
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('weight')
            )['total'] or Decimal('0')
            total_with_self = other_weights + self.weight
            if total_with_self > Decimal('100'):
                errors['weight'] = (
                    f"La suma de ponderadores para este cargo y período "
                    f"sería {total_with_self}%, superando el 100% "
                    f"permitido (RN-001). Ponderador ya asignado a otras "
                    f"metas del mismo cargo/período: {other_weights}%."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Meta {self.item_name} — {self.position} ({self.period})"


class Commitment(SoftDeleteModel):

    STATUS_INGRESADO = 'ingresado'
    STATUS_PENDIENTE = 'pendiente'
    STATUS_EN_PROCESO = 'en_proceso'
    STATUS_REALIZADO = 'realizado'
    STATUS_CHOICES = [
        (STATUS_INGRESADO, 'Ingresado'),
        (STATUS_PENDIENTE, 'Pendiente'),
        (STATUS_EN_PROCESO, 'En proceso'),
        (STATUS_REALIZADO, 'Realizado'),
    ]

    delegation = models.ForeignKey(
        Delegation, on_delete=models.PROTECT, related_name='commitments'
    )
    responsible = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='commitments'
    )
    origin = models.CharField(max_length=150)
    requester = models.CharField(max_length=150)
    territory = models.CharField(max_length=100)
    due_date = models.DateField()
    support_area = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_INGRESADO
    )
    observation = models.TextField(blank=True, max_length=2000)

    def clean(self):
        super().clean()
        if self.responsible_id is None or self.delegation_id is None:
            return
        if self.responsible.delegation_id != self.delegation_id:
            raise ValidationError({
                'delegation': (
                    f"La delegación ({self.delegation}) no coincide con "
                    f"la delegación del responsable asignado "
                    f"({self.responsible.delegation})."
                )
            })

    def __str__(self):
        return f"Compromiso {self.pk} — {self.origin} ({self.get_status_display()})"


class Activity(SoftDeleteModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='activities'
    )
    period = models.ForeignKey(
        Period, on_delete=models.PROTECT, related_name='activities'
    )
    meta = models.ForeignKey(
        Meta, on_delete=models.PROTECT, related_name='activities',
        null=True, blank=True,
    )
    activity_type = models.CharField(max_length=100)
    service = models.CharField(max_length=100)
    attention = models.ForeignKey(
        CatalogItem,
        on_delete=models.PROTECT,
        related_name='activities',
        limit_choices_to={'category': CatalogItem.CATEGORY_ATTENTION},
    )
    sub_attention = models.CharField(max_length=100)
    date = models.DateField()
    request_description = models.TextField(max_length=3000)
    action_taken = models.TextField(max_length=3000)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=30)

    def clean(self):
        super().clean()
        if self.period_id is None or self.date is None:
            return
        if not (self.period.start_date <= self.date <= self.period.end_date):
            raise ValidationError({
                'date': (
                    f"La fecha ({self.date}) debe estar dentro del "
                    f"período asignado ({self.period.start_date} – "
                    f"{self.period.end_date})."
                )
            })

    def __str__(self):
        return f"Actividad {self.pk} — {self.activity_type}"

    def _before_soft_delete(self):

        live_evidence = self.evidence_items.all()
        if live_evidence.exists():
            raise ProtectedError(
                "No se puede eliminar la actividad porque tiene evidencias "
                "asociadas. Elimine primero sus evidencias.",
                set(live_evidence),
            )


class Evidence(SoftDeleteModel):

    REVIEW_STATUS_PENDIENTE = 'pendiente'
    REVIEW_STATUS_APROBADA = 'aprobada'
    REVIEW_STATUS_RECHAZADA = 'rechazada'
    REVIEW_STATUS_CHOICES = [
        (REVIEW_STATUS_PENDIENTE, 'Pendiente'),
        (REVIEW_STATUS_APROBADA, 'Aprobada'),
        (REVIEW_STATUS_RECHAZADA, 'Rechazada'),
    ]

    CODE_PREFIX = 'EVID-'
    CODE_DIGITS = 4
    CODE_MAX_ATTEMPTS = 10
    _CODE_RE = re.compile(rf'^{re.escape(CODE_PREFIX)}(\d+)$', re.IGNORECASE)

    code = models.CharField(
        max_length=30, primary_key=True, editable=False,
        help_text=(
            'Lo asigna el sistema al guardar (EVID-0001, EVID-0002...) y no '
            'se puede cambiar.'
        ),
    )
    activity = models.ForeignKey(
        Activity, on_delete=models.PROTECT, related_name='evidence_items'
    )
    file = models.FileField(upload_to='evidence/%Y/%m/', validators=[validate_evidence_file],)
    date = models.DateField()
    metadata = models.TextField(blank=True, max_length=2000)
    review_status = models.CharField(
        max_length=30,
        choices=REVIEW_STATUS_CHOICES,
        default=REVIEW_STATUS_PENDIENTE,
    )

    def __str__(self):
        return self.code

    @classmethod
    def next_code(cls):

        codes = cls.all_objects.filter(
            code__istartswith=cls.CODE_PREFIX
        ).values_list('code', flat=True)
        last = 0
        for code in codes.iterator():
            match = cls._CODE_RE.match(code)
            if match:
                last = max(last, int(match.group(1)))
        return f'{cls.CODE_PREFIX}{last + 1:0{cls.CODE_DIGITS}d}'

    def save(self, *args, **kwargs):

        if self._state.adding and not self.code:
            self._save_with_new_code(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def _save_with_new_code(self, *args, **kwargs):

        kwargs['force_insert'] = True
        for attempt in range(1, self.CODE_MAX_ATTEMPTS + 1):
            self.code = self.next_code()
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                return
            except IntegrityError:

                taken = type(self).all_objects.filter(pk=self.code).exists()
                if not taken or attempt == self.CODE_MAX_ATTEMPTS:
                    self.code = ''
                    raise

    def _before_soft_delete(self):

        for validation in Validation.objects.filter(evidence=self):
            validation.soft_delete()


class Validation(SoftDeleteModel):

    evidence = models.OneToOneField(
        Evidence, on_delete=models.CASCADE, related_name='validation'
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='validations_performed'
    )
    decision = models.CharField(max_length=30)
    date = models.DateField()
    notes = models.TextField(blank=True, max_length=2000)
    result = models.BooleanField()
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Validación {self.pk} — {self.evidence_id}"
