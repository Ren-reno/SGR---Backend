"""CRUD web de Evidence (Fase 6, paso 6.2): listar, crear y editar.

Mismo patrón que `views/activity.py`; la eliminación (SweetAlert2 + borrado
lógico) llega en el patch final.

Capas de control, todas del lado del servidor:
- Permiso de modelo (`PermissionRequiredMixin`): los mismos que usa el Admin y
  asigna `seed_sgr` -- Funcionario y Verificador ven y editan, solo
  Administrador crea; Delegado no tiene ninguno. Sin sesión redirige al login;
  con sesión pero sin permiso responde 403.
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

from performance.forms import EvidenceForm
from performance.models import Evidence
from performance.pagination import SessionPaginationMixin
from performance.scoping import DelegationScopedQuerysetMixin


class EvidenceListView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    SessionPaginationMixin, ListView,
):
    model = Evidence
    template_name = 'performance/evidence_list.html'
    context_object_name = 'evidences'
    permission_required = 'performance.view_evidence'
    delegation_lookup = 'activity__employee__'
    # `-pk` (el código) desempata evidencias del mismo día para que ninguna
    # cambie de página al recargar.
    ordering = ('-date', '-pk')

    def get_queryset(self):
        return super().get_queryset().select_related(
            'activity', 'activity__employee',
        )


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
    success_message = 'Evidencia registrada.'
    extra_context = {'page_title': 'Nueva evidencia'}


class EvidenceUpdateView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    _EvidenceFormMixin, SuccessMessageMixin, UpdateView,
):
    permission_required = 'performance.change_evidence'
    delegation_lookup = 'activity__employee__'
    success_message = 'Evidencia actualizada.'
    extra_context = {'page_title': 'Editar evidencia'}
