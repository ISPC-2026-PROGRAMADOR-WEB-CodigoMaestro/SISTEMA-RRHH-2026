from django.contrib import admin

from .models import (
    ConfiguracionAsistencia,
    HorarioDiario,
    HorarioPredeterminado,
)


@admin.register(ConfiguracionAsistencia)
class ConfiguracionAsistenciaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ConfiguracionAsistencia.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HorarioDiario)
class HorarioDiarioAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'hora_entrada', 'hora_salida', 'es_franco')
    list_filter = ('es_franco', 'fecha')
    search_fields = ('empleado__legajo', 'empleado__apellido', 'empleado__nombre')
    autocomplete_fields = ('empleado', 'creado_por')
    date_hierarchy = 'fecha'


@admin.register(HorarioPredeterminado)
class HorarioPredeterminadoAdmin(admin.ModelAdmin):
    list_display = (
        'empleado',
        'vigente_desde',
        'hora_entrada',
        'hora_salida',
        'creado_por',
    )
    list_filter = ('vigente_desde',)
    search_fields = ('empleado__legajo', 'empleado__apellido', 'empleado__nombre')
    autocomplete_fields = ('empleado', 'creado_por')
    date_hierarchy = 'vigente_desde'
