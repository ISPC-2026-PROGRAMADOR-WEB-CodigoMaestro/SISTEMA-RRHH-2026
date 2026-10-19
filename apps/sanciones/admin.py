from django.contrib import admin
from .models import Sancion


@admin.register(Sancion)
class SancionAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo', 'fecha_hecho', 'estado', 'responsable')
    list_filter = ('tipo', 'estado')
    search_fields = ('empleado__legajo', 'empleado__apellido', 'descripcion')
    autocomplete_fields = ('empleado', 'responsable')
    date_hierarchy = 'fecha_hecho'
