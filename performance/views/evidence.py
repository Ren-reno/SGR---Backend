"""CRUD web de Evidence: listar, crear y editar (Fase 6, paso 6.2) y eliminar
(Fase 6, paso 6.3 / Fase 7, Decisión 28). Incluye filtros en el listado
(Fase 9).

Mismo patrón que `views/activity.py`.

Capas de control, todas del lado del servidor:
- Permiso de modelo (`PermissionRequiredMixin`): los mismos que usa el Admin y
  asigna `seed_sgr` -- Funcionario y Verificador ven y editan, solo
  Administrador crea y elimina; Delegado no tiene ninguno. Sin sesión redirige
  al login; con sesión pero sin permiso responde 403.
- Scoping por Delegación (`DelegationScopedQuerysetMixin`): en el listado
  filtra las filas; en la edición hace que una evidencia ajena responda 404.
- Valores escritos: `EvidenceForm` acota el desplegable `activity`.

Particularidades de `Evidence`: su clave primaria es el código (texto), no un
número, y lleva un archivo. `CreateView`/`UpdateView` ya pasan `request.FILES`
al formulario; lo que sí hace falta es `enctype="multipart/form-data"` en el
template.
"""
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from organization.models import Employee
from performance.deletion import SoftDeleteView
from performance.forms import EvidenceForm
from performance.models import Evidence
from performance.pagination import SessionPaginationMixin
from performance.scoping import DelegationScopedQuerysetMixin, scope_queryset_for_user


class EvidenceListView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    SessionPaginationMixin, ListView,
):
    model = Evidence
    template_name = 'performance/evidence_list.html'
    context_object_name = 'evidences'
    permission_required = 'performance.view_evidence'
    delegation_lookup = 'activity__employee__'
    ordering = ('-date', '-pk')

    def get_queryset(self):
        qs = super().get_queryset().select_related('activity', 'activity__employee')
        params = self.request.GET
        if params.get('date_from'):
            qs = qs.filter(date__gte=params['date_from'])
        if params.get('date_to'):
            qs = qs.filter(date__lte=params['date_to'])
        if params.get('employee'):
            qs = qs.filter(activity__employee_id=params['employee'])
        if params.get('review_status'):
            qs = qs.filter(review_status=params['review_status'])
        if params.get('code'):
            qs = qs.filter(code__icontains=params['code'])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_employees'] = scope_queryset_for_user(
            Employee.objects.order_by('name'), self.request.user, '',
        )
        context['filter_review_statuses'] = Evidence.REVIEW_STATUS_CHOICES
        context['filter_values'] = self.request.GET
        return context


class _EvidenceFormMixin:
    model = Evidence
    form_class = EvidenceForm
    template_name = 'performance/evidence_form.html'
    success_url = reverse_lazy('performance:evidence_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class EvidenceCreateView(
    PermissionRequiredMixin, _EvidenceFormMixin, SuccessMessageMixin, CreateView,
):
    permission_required = 'performance.add_evidence'
    extra_context = {'page_title': 'Nueva evidencia'}

    def get_success_message(self, cleaned_data):
        return f'Evidencia {self.object.code} registrada.'


class EvidenceUpdateView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    _EvidenceFormMixin, SuccessMessageMixin, UpdateView,
):
    permission_required = 'performance.change_evidence'
    delegation_lookup = 'activity__employee__'
    success_message = 'Evidencia actualizada.'
    extra_context = {'page_title': 'Editar evidencia'}


class EvidenceDeleteView(SoftDeleteView):
    """Borrado lógico (`deleted_at`). Eliminar una evidencia elimina también
    su validación, si la tiene (`Evidence._before_soft_delete`, Decisión 26
    punto 2): por eso el botón del listado lo avisa antes de confirmar.

    La clave primaria es el código (texto), así que la ruta usa `<path:pk>`,
    igual que la de edición.
    """
    model = Evidence
    permission_required = 'performance.delete_evidence'
    delegation_lookup = 'activity__employee__'
    success_url = reverse_lazy('performance:evidence_list')
    success_message = 'Evidencia eliminada.'