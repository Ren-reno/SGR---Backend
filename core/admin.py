from django.contrib import admin
from .models import Delegacion, Cargo, Funcionario, Periodo, Actividad, Evidencia, Validacion

admin.site.register(Delegacion)
admin.site.register(Cargo)
admin.site.register(Funcionario)
admin.site.register(Periodo)
admin.site.register(Actividad)
admin.site.register(Evidencia)
admin.site.register(Validacion)