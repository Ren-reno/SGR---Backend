"""CRUD web de Commitment (Fase 6, paso 6.4): listar, crear y editar.

Mismo patrón que `views/activity.py` (6.1); la eliminación (SweetAlert2 +
borrado lógico) llega en el patch final.

Capas de control, todas del lado del servidor:
- Permiso de modelo (`PermissionRequiredMixin`): los mismos que ya usa el
  Admin y asigna `seed_sgr` (Decisión 18) -- Administrador y Funcionario
  ven, crean y editan; Verificador y Delegado no tienen ninguno, así que
  reciben 403. Sin sesión redirige al login.
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

from performance.forms import CommitmentForm
from performance.models import Commitment
from performance.pagination import SessionPaginationMixin
from performance.scoping import DelegationScopedQuerysetMixin


class CommitmentListView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    SessionPaginationMixin, ListView,
):
    model = Commitment
    template_name = 'performance/commitment_list.html'
    context_object_name = 'commitments'
    permission_required = 'performance.view_commitment'
    delegation_lookup = ''  # FK directa: Commitment.delegation
    # Mismo orden que el Admin; `-pk` desempata compromisos con la misma
    # fecha para que ninguno cambie de página al recargar.
    ordering = ('-due_date', '-pk')

    def get_queryset(self):
        return super().get_queryset().select_related(
            'delegation', 'responsible',
        )


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
