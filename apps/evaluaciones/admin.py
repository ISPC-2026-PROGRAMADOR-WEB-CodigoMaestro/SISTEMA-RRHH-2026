from django.contrib import admin
from .models import PeriodoEvaluacion, CriterioEvaluacion, EvaluacionDesempeno, DetalleEvaluacion


class DetalleEvaluacionInline(admin.TabularInline):
    model = DetalleEvaluacion
    extra = 0
    autocomplete_fields = ('criterio',)


@admin.register(PeriodoEvaluacion)
class PeriodoEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)


@admin.register(CriterioEvaluacion)
class CriterioEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'peso', 'orden', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)


@admin.register(EvaluacionDesempeno)
class EvaluacionDesempenoAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'periodo', 'fecha_evaluacion', 'calificacion_general', 'estado')
    list_filter = ('estado', 'periodo')
    search_fields = ('empleado__legajo', 'empleado__apellido')
    autocomplete_fields = ('empleado', 'periodo', 'evaluador')
    inlines = [DetalleEvaluacionInline]


@admin.register(DetalleEvaluacion)
class DetalleEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('evaluacion', 'criterio', 'calificacion')
    autocomplete_fields = ('evaluacion', 'criterio')
