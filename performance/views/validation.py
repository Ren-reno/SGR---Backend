"""CRUD web de Validation (Fase 6, paso 6.3): listar, crear y editar.

La eliminación (SweetAlert2 + borrado lógico) llega en el patch final.

Reproduce a `ValidationAdmin` (no lo reinventa). Capas de control, todas del
lado del servidor:
- Permiso de modelo (`PermissionRequiredMixin`): `view_/add_/change_validation`,
  los mismos que asigna `seed_sgr` (Administrador todo; Verificador ver,
  crear y editar; Funcionario y Delegado ninguno).
- Rol, solo en alta y edición: además del permiso, `ValidationAdmin` exige
  ser Verificador o Administrador (`has_add_permission` /
  `has_change_permission`). Sin este segundo chequeo, un usuario al que
  alguien le dé `add_validation` a mano podría revisar evidencias sin ser
  verificador. El listado NO lo exige: el Admin tampoco (solo permiso de
  modelo y scoping).
- Scoping por Delegación (`DelegationScopedQuerysetMixin`): en el listado
  filtra las filas; en la edición hace que una validación ajena responda 404.
- Valores escritos: `ValidationForm` acota `evidence` y `employee`.
"""
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from performance.forms import DECISION_REJECTED, ValidationForm
from performance.models import Validation
from performance.pagination import SessionPaginationMixin
from performance.scoping import DelegationScopedQuerysetMixin

# Mismos roles que `_is_verifier(request) or _unrestricted(request)` en
# performance/admin.py: superuser, grupo Administrador o grupo Verificador.
REVIEWER_GROUPS = ('Administrador', 'Verificador')


def user_can_review(user):
    """True si `user` puede emitir o modificar revisiones (rol, no permiso)."""
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name__in=REVIEWER_GROUPS).exists()
    )


class ReviewerPermissionMixin(PermissionRequiredMixin):
    """Permiso de modelo + rol de revisor. Pública a propósito: el patch de
    eliminación la reutiliza (en el Admin, `has_delete_permission` aplica el
    mismo rol)."""

    def has_permission(self):
        return super().has_permission() and user_can_review(self.request.user)


class ValidationListView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin,
    SessionPaginationMixin, ListView,
):
    model = Validation
    template_name = 'performance/validation_list.html'
    context_object_name = 'validations'
    permission_required = 'performance.view_validation'
    delegation_lookup = 'evidence__activity__employee__'
    # `ordering` es obligatorio (ver SessionPaginationMixin); `-pk` desempata
    # revisiones del mismo día para que ninguna cambie de página al recargar.
    ordering = ('-date', '-pk')

    def get_queryset(self):
        return super().get_queryset().select_related(
            'evidence__activity__employee', 'employee',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # El botón "Nueva validación" depende del permiso Y del rol (ver el
        # docstring del módulo); el template no puede consultar el grupo.
        context['can_review'] = user_can_review(self.request.user)
        context['decision_rejected'] = DECISION_REJECTED
        return context


class _ValidationFormMixin:
    model = Validation
    form_class = ValidationForm
    template_name = 'performance/validation_form.html'
    success_url = reverse_lazy('performance:validation_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ValidationCreateView(
    ReviewerPermissionMixin, _ValidationFormMixin, SuccessMessageMixin, CreateView,
):
    permission_required = 'performance.add_validation'
    success_message = 'Validación registrada.'
    extra_context = {'page_title': 'Nueva validación'}


class ValidationUpdateView(
    ReviewerPermissionMixin, DelegationScopedQuerysetMixin,
    _ValidationFormMixin, SuccessMessageMixin, UpdateView,
):
    permission_required = 'performance.change_validation'
    delegation_lookup = 'evidence__activity__employee__'
    success_message = 'Validación actualizada.'
    extra_context = {'page_title': 'Editar validación'}
