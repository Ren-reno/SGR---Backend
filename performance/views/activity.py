from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import View
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from performance.deletion import SoftDeleteView
from performance.forms import ActivityForm
from performance.models import Activity
from performance.pagination import SessionPaginationMixin
from performance.scoping import DelegationScopedQuerysetMixin


class ActivityListView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    SessionPaginationMixin, ListView,
):
    model = Activity
    template_name = 'performance/activity_list.html'
    context_object_name = 'activities'
    permission_required = 'performance.view_activity'
    delegation_lookup = 'employee__'
    # `ordering` es obligatorio (ver SessionPaginationMixin); `-pk` desempata
    # actividades del mismo día para que ninguna cambie de página al recargar.
    ordering = ('-date', '-pk')

    def get_queryset(self):
        return super().get_queryset().select_related(
            'employee', 'period', 'meta', 'attention',
        )


class _ActivityFormMixin:
    model = Activity
    form_class = ActivityForm
    template_name = 'performance/activity_form.html'
    success_url = reverse_lazy('performance:activity_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ActivityCreateView(
    PermissionRequiredMixin, _ActivityFormMixin, SuccessMessageMixin, CreateView,
):
    permission_required = 'performance.add_activity'
    success_message = 'Actividad registrada.'
    extra_context = {'page_title': 'Nueva actividad'}


class ActivityUpdateView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    _ActivityFormMixin, SuccessMessageMixin, UpdateView,
):
    permission_required = 'performance.change_activity'
    delegation_lookup = 'employee__'
    success_message = 'Actividad actualizada.'
    extra_context = {'page_title': 'Editar actividad'}


class ActivityDeleteView(SoftDeleteView):
    """Borrado lógico (`deleted_at`). Una actividad con evidencias vivas no
    se elimina: `Activity._before_soft_delete` lanza `ProtectedError` y la
    vista base lo muestra como mensaje."""
    model = Activity
    permission_required = 'performance.delete_activity'
    delegation_lookup = 'employee__'
    success_url = reverse_lazy('performance:activity_list')
    success_message = 'Actividad eliminada.'

class ActivityExportView(PermissionRequiredMixin, DelegationScopedQuerysetMixin, View):
    """Exporta a .xlsx las Activity visibles para el usuario actual (Fase 9,
    paso 9.2). Reutiliza get_scoped_queryset() de DelegationScopedQuerysetMixin
    -- mismo scoping por Delegación y mismo soft-delete que ActivityListView,
    no una consulta aparte sin esos filtros.
    """
    model = Activity
    permission_required = 'performance.view_activity'
    delegation_lookup = 'employee__'

    COLUMNS = [
        ('ID', 'pk'),
        ('Fecha', 'date'),
        ('Funcionario', 'employee'),
        ('Período', 'period'),
        ('Meta', 'meta'),
        ('Tipo de actividad', 'activity_type'),
        ('Servicio', 'service'),
        ('Atención', 'attention'),
        ('Subatención', 'sub_attention'),
        ('Descripción de la solicitud', 'request_description'),
        ('Acción realizada', 'action_taken'),
        ('Contacto', 'contact_name'),
        ('Teléfono', 'contact_phone'),
        ('Estado', 'status'),
    ]

    def get(self, request, *args, **kwargs):
        queryset = self.get_scoped_queryset().select_related(
            'employee', 'period', 'meta', 'attention',
        ).order_by('-date', '-pk')

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Actividades'

        headers = [label for label, _ in self.COLUMNS]
        sheet.append(headers)
        for col_index in range(1, len(headers) + 1):
            sheet.column_dimensions[get_column_letter(col_index)].width = 22

        for activity in queryset.iterator():
            row = []
            for _, field in self.COLUMNS:
                value = activity.pk if field == 'pk' else getattr(activity, field)
                row.append(str(value) if value is not None else '')
            sheet.append(row)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        filename = f'actividades_{timezone.now():%Y%m%d_%H%M}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        workbook.save(response)
        return response