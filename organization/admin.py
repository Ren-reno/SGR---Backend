from django.contrib import admin

from .models import Delegation, Position, Employee


@admin.register(Delegation)
class DelegationAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('id', 'name', 'scope', 'is_active')
    search_fields = ('id', 'name')
    list_filter = ('scope', 'is_active')
    ordering = ('name',)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    ordering = ('name',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Fase 5 y 6 extienden esta clase — no la dupliques
    list_display = ('institutional_id', 'name', 'delegation', 'position', 'user', 'is_active')
    search_fields = ('institutional_id', 'name', 'user__username')
    list_filter = ('delegation', 'position', 'is_active')
    ordering = ('name',)
    list_select_related = ('delegation', 'position', 'user')
