"""CRUD web de Activity (Fase 6, paso 6.1): listar, crear y editar.

La eliminación (SweetAlert2 + borrado lógico) llega en el patch final.

Capas de control, todas del lado del servidor:
- Permiso de modelo (`PermissionRequiredMixin`): los mismos que ya usa el
  Admin y asigna `seed_sgr` -- Funcionario/Verificador ven y editan,
  solo Administrador crea; Delegado no tiene ninguno todavía. Sin sesión
  redirige al login; con sesión pero sin permiso responde 403.
- Scoping por Delegación (`DelegationScopedQuerysetMixin`): en el listado
  filtra las filas; en la edición hace que una actividad ajena responda 404.
- Valores escritos: `ActivityForm` acota el desplegable `employee`.
"""
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

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
