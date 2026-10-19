from django.contrib import admin
from .models import TipoLicencia, SaldoVacaciones, SolicitudLicencia


@admin.register(TipoLicencia)
class TipoLicenciaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'dias_maximos', 'requiere_aprobacion', 'descuenta_vacaciones', 'activo')
    list_filter = ('activo', 'requiere_aprobacion', 'descuenta_vacaciones')
    search_fields = ('codigo', 'nombre')


@admin.register(SaldoVacaciones)
class SaldoVacacionesAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'anio', 'dias_correspondientes', 'dias_usados', 'dias_pendientes')
    list_filter = ('anio',)
    search_fields = ('empleado__legajo', 'empleado__apellido')
    autocomplete_fields = ('empleado',)


@admin.register(SolicitudLicencia)
class SolicitudLicenciaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo_licencia', 'fecha_inicio', 'fecha_fin', 'dias_solicitados', 'estado')
    list_filter = ('estado', 'tipo_licencia')
    search_fields = ('empleado__legajo', 'empleado__apellido')
    autocomplete_fields = ('empleado', 'tipo_licencia', 'solicitado_por', 'revisado_por')
    date_hierarchy = 'fecha_inicio'
