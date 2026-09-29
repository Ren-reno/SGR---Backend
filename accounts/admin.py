from django.contrib import admin

from .models import PasswordResetCode


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    """Los códigos de recuperación se ven acá para poder demostrar el flujo
    sin correo real (paso 4.3), pero el modelo es de SOLO LECTURA: nadie
    debe crear ni editar un código a mano, porque eso permitiría fijar un
    código conocido y tomar la cuenta de otro usuario sin pasar por el flujo
    normal. Se puede borrar (para limpiar), no fabricar ni modificar."""

    list_display = ('user', 'code', 'status', 'created_at', 'expires_at',
                    'used_at', 'failed_attempts')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    ordering = ('-created_at',)
    list_select_related = ('user',)
    readonly_fields = ('user', 'code', 'created_at', 'expires_at', 'used_at',
                       'failed_attempts')

    @admin.display(description='Estado')
    def status(self, obj):
        return obj.status

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
