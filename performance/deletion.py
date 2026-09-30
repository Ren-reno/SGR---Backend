"""Vista base de eliminación web con borrado lógico (Fase 7, Decisión 26).

Igual que `scoping.py` y `pagination.py`, vive a nivel de la app porque las
4 entidades del CRUD web la reutilizan: cada vista concreta solo declara
`model`, `permission_required`, `delegation_lookup`, `success_url` y el
mensaje de éxito.

Capas de control, todas del lado del servidor (la confirmación de
SweetAlert2 en el navegador es solo una ayuda visual y NO reemplaza nada de
esto):

1. Solo `POST`. Un `GET` responde 405: eliminar nunca ocurre por un enlace.
   El middleware de Django exige además el token CSRF.
2. Autenticación + permiso de modelo (`PermissionRequiredMixin`,
   `delete_<modelo>`): sin sesión redirige al login; sin permiso, 403.
3. Scoping por Delegación (`DelegationScopedQuerysetMixin`): un registro de
   otra Delegación no está en el queryset, así que responde 404.
4. Borrado lógico: `object.delete()` en un `SoftDeleteModel` solo marca
   `deleted_at` (ver `soft_delete.py`); la fila nunca se borra físicamente.
5. Las reglas propias de cada modelo (`_before_soft_delete`) siguen valiendo:
   si impiden el borrado lanzan `ProtectedError`, que se muestra como
   mensaje en el listado en vez de una pantalla 500.
"""
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.views.generic import DeleteView

from .scoping import DelegationScopedQuerysetMixin


class SoftDeleteView(
    PermissionRequiredMixin, DelegationScopedQuerysetMixin, DeleteView,
):
    """Subclase mínima:

        class ActivityDeleteView(SoftDeleteView):
            model = Activity
            permission_required = 'performance.delete_activity'
            delegation_lookup = 'employee__'
            success_url = reverse_lazy('performance:activity_list')
            success_message = 'Actividad eliminada.'
    """

    # Sin 'get': no hay pantalla de confirmación por GET; la confirmación
    # es el SweetAlert2 del listado.
    http_method_names = ['post', 'options']
    success_message = 'Registro eliminado.'
    already_deleted_message = 'El registro ya estaba eliminado.'

    def form_valid(self, form):
        success_url = self.get_success_url()
        try:
            deleted, _ = self.object.delete()
        except ProtectedError as error:
            # Regla de negocio del modelo: el mensaje ya viene redactado
            # para la persona usuaria. Se vuelve al listado sin cambios.
            messages.error(self.request, str(error.args[0]))
        else:
            if deleted:
                messages.success(self.request, self.success_message)
            else:
                # Carrera entre dos envíos: el registro ya estaba oculto.
                messages.info(self.request, self.already_deleted_message)
        return HttpResponseRedirect(success_url)
