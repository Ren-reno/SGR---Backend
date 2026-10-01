"""CRUD web de Commitment: listar, crear y editar (Fase 6, paso 6.4) y
eliminar (Fase 6, paso 6.3 / Fase 7, Decisión 28). Incluye filtros en el
listado (Fase 9).

Mismo patrón que `views/activity.py` (6.1).

Capas de control, todas del lado del servidor:
- Permiso de modelo (`PermissionRequiredMixin`): los mismos que ya usa el
  Admin y asigna `seed_sgr` (Decisión 18) -- Administrador y Funcionario
  ven, crean y editan (solo el Administrador elimina); Verificador y
  Delegado no tienen ninguno, así que reciben 403. Sin sesión redirige al
  login.
- Scoping por Delegación (`DelegationScopedQuerysetMixin`): en el listado
  filtra las filas; en la edición hace que un compromiso ajeno responda 404.
  Se filtra por `Commitment.delegation` (la propia del compromiso, no la de
  su responsable actual), igual que `CommitmentAdmin` (Decisión 18).
- Valores escritos: `CommitmentForm` acota los desplegables `delegation` y
  `responsible`.
"""
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from organization.models import Delegation, Employee
from performance.deletion import SoftDeleteView
from performance.forms import CommitmentForm
from performance.models import Commitment
from performance.pagination import SessionPaginationMixin
from performance.scoping import (
    DelegationScopedQuerysetMixin,
    scope_delegations_for_user,
    scope_queryset_for_user,
)


class CommitmentListView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    SessionPaginationMixin, ListView,
):
    model = Commitment
    template_name = 'performance/commitment_list.html'
    context_object_name = 'commitments'
    permission_required = 'performance.view_commitment'
    delegation_lookup = ''  # FK directa: Commitment.delegation
    ordering = ('-due_date', '-pk')

    def get_queryset(self):
        qs = super().get_queryset().select_related('delegation', 'responsible')
        params = self.request.GET
        if params.get('date_from'):
            qs = qs.filter(due_date__gte=params['date_from'])
        if params.get('date_to'):
            qs = qs.filter(due_date__lte=params['date_to'])
        if params.get('responsible'):
            qs = qs.filter(responsible_id=params['responsible'])
        if params.get('delegation'):
            qs = qs.filter(delegation_id=params['delegation'])
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # delegation_lookup='' para Employee: es una FK directa a Delegation.
        context['filter_employees'] = scope_queryset_for_user(
            Employee.objects.order_by('name'), self.request.user, '',
        )
        context['filter_delegations'] = scope_delegations_for_user(
            Delegation.objects.order_by('name'), self.request.user,
        )
        context['filter_statuses'] = Commitment.STATUS_CHOICES
        context['filter_values'] = self.request.GET
        return context


class _CommitmentFormMixin:
    model = Commitment
    form_class = CommitmentForm
    template_name = 'performance/commitment_form.html'
    success_url = reverse_lazy('performance:commitment_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class CommitmentCreateView(
    PermissionRequiredMixin, _CommitmentFormMixin, SuccessMessageMixin,
    CreateView,
):
    permission_required = 'performance.add_commitment'
    success_message = 'Compromiso registrado.'
    extra_context = {'page_title': 'Nuevo compromiso'}


class CommitmentUpdateView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    _CommitmentFormMixin, SuccessMessageMixin, UpdateView,
):
    permission_required = 'performance.change_commitment'
    delegation_lookup = ''
    success_message = 'Compromiso actualizado.'
    extra_context = {'page_title': 'Editar compromiso'}


class CommitmentDeleteView(SoftDeleteView):
    """Borrado lógico (`deleted_at`). `Commitment` no tiene reglas propias
    de borrado (ni hijos ni `ProtectedError`): solo permiso y Delegación,
    igual que `CommitmentAdmin` (Decisión 18). Se acota por
    `Commitment.delegation`, no por la de su responsable."""
    model = Commitment
    permission_required = 'performance.delete_commitment'
    delegation_lookup = ''
    success_url = reverse_lazy('performance:commitment_list')
    success_message = 'Compromiso eliminado.'