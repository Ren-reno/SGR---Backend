"""CRUD web de Validation: listar, crear y editar (Fase 6, paso 6.3) y eliminar
(Fase 6, paso 6.3 / Fase 7, Decisión 29). Incluye filtros en el listado
(Fase 9).

Reproduce a `ValidationAdmin` (no lo reinventa). Capas de control, todas del
lado del servidor:
- Permiso de modelo (`PermissionRequiredMixin`): `view_/add_/change_validation`,
  los mismos que asigna `seed_sgr` (Administrador todo; Verificador ver,
  crear y editar; Funcionario y Delegado ninguno).
- Rol, solo en alta, edición y eliminación: además del permiso,
  `ValidationAdmin` exige ser Verificador o Administrador
  (`has_add_permission` / `has_change_permission` / `has_delete_permission`).
  Sin este segundo chequeo, un usuario al que alguien le dé `add_validation`
  (o `delete_validation`) a mano podría revisar o eliminar revisiones sin ser
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

from organization.models import Employee
from performance.deletion import SoftDeleteView
from performance.forms import DECISION_REJECTED, ValidationForm
from performance.models import Validation
from performance.pagination import SessionPaginationMixin
from performance.scoping import DelegationScopedQuerysetMixin, scope_queryset_for_user

REVIEWER_GROUPS = ('Administrador', 'Verificador')


def user_can_review(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name__in=REVIEWER_GROUPS).exists()
    )


class ReviewerPermissionMixin(PermissionRequiredMixin):
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
    ordering = ('-date', '-pk')

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'evidence__activity__employee', 'employee',
        )
        params = self.request.GET
        if params.get('date_from'):
            qs = qs.filter(date__gte=params['date_from'])
        if params.get('date_to'):
            qs = qs.filter(date__lte=params['date_to'])
        if params.get('employee'):
            qs = qs.filter(employee_id=params['employee'])
        if params.get('result') in ('true', 'false'):
            qs = qs.filter(result=(params['result'] == 'true'))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_review'] = user_can_review(self.request.user)
        context['decision_rejected'] = DECISION_REJECTED
        # Verificadores del propio ámbito, para el filtro (mismo criterio de
        # scoping que el resto del listado).
        context['filter_employees'] = scope_queryset_for_user(
            Employee.objects.filter(
                user__groups__name__in=REVIEWER_GROUPS,
            ).distinct().order_by('name'),
            self.request.user, '',
        )
        context['filter_values'] = self.request.GET
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


class ValidationDeleteView(ReviewerPermissionMixin, SoftDeleteView):
    model = Validation
    permission_required = 'performance.delete_validation'
    delegation_lookup = 'evidence__activity__employee__'
    success_url = reverse_lazy('performance:validation_list')
    success_message = 'Validación eliminada.'