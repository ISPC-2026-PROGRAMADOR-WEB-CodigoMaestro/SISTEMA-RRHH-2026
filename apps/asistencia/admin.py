from django.contrib import admin
from .models import AsignacionJornada, Feriado, Jornada, Marcacion, RegistroAsistencia, Turno


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'hora_inicio', 'hora_fin', 'minutos_tolerancia', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)


@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'empleado', 'dia_semana', 'turno', 'hora_entrada',
        'hora_salida', 'es_predeterminada', 'activa',
    )
    list_filter = ('es_predeterminada', 'dia_semana', 'activa', 'turno')
    search_fields = ('nombre', 'empleado__legajo', 'empleado__apellido', 'turno__nombre')
    autocomplete_fields = ('empleado', 'turno')


@admin.register(AsignacionJornada)
class AsignacionJornadaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'jornada')
    search_fields = ('empleado__legajo', 'empleado__apellido', 'jornada__nombre')
    autocomplete_fields = ('empleado', 'jornada')


@admin.register(Feriado)
class FeriadoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'nombre')
    search_fields = ('nombre',)
    date_hierarchy = 'fecha'


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'tipo', 'hora_ingreso', 'hora_egreso', 'justificado')
    list_filter = ('tipo', 'justificado', 'fecha')
    search_fields = ('empleado__legajo', 'empleado__apellido')
    autocomplete_fields = ('empleado', 'cargado_por')
    date_hierarchy = 'fecha'


@admin.register(Marcacion)
class MarcacionAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha_hora', 'tipo', 'origen', 'cargado_por')
    list_filter = ('tipo', 'origen', 'fecha_hora')
    search_fields = ('empleado__legajo', 'empleado__apellido')
    autocomplete_fields = ('empleado', 'cargado_por')
    date_hierarchy = 'fecha_hora'
