from django.contrib import admin
from .models import RegistroAsistencia


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'tipo', 'hora_ingreso', 'hora_egreso', 'justificado')
    list_filter = ('tipo', 'justificado', 'fecha')
    search_fields = ('empleado__legajo', 'empleado__apellido')
    autocomplete_fields = ('empleado', 'cargado_por')
    date_hierarchy = 'fecha'
