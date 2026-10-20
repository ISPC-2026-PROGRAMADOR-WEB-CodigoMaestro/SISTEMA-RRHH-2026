from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import PeriodoEvaluacion, CriterioEvaluacion, EvaluacionDesempeno, DetalleEvaluacion
from .services import cambiar_estado_evaluacion


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
    readonly_fields = ('estado', 'calificacion_general', 'fecha_creacion', 'fecha_actualizacion')
    actions = ('iniciar_seleccionadas', 'finalizar_seleccionadas', 'anular_seleccionadas')

    def _transicionar(self, request, queryset, accion):
        actualizadas = 0
        for evaluacion in queryset:
            try:
                cambiar_estado_evaluacion(evaluacion.pk, accion, request.user)
            except ValidationError as exc:
                errors = (
                    [error for field_errors in exc.message_dict.values() for error in field_errors]
                    if hasattr(exc, 'message_dict') else exc.messages
                )
                self.message_user(
                    request,
                    f'{evaluacion}: {"; ".join(str(error) for error in errors)}',
                    level='error',
                )
            else:
                actualizadas += 1
        if actualizadas:
            self.message_user(request, f'{actualizadas} evaluación(es) actualizadas.')

    @admin.action(description='Iniciar evaluaciones en borrador')
    def iniciar_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, 'iniciar')

    @admin.action(description='Finalizar evaluaciones en curso')
    def finalizar_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, 'finalizar')

    @admin.action(description='Anular evaluaciones en borrador o en curso')
    def anular_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, 'anular')


@admin.register(DetalleEvaluacion)
class DetalleEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('evaluacion', 'criterio', 'calificacion')
    autocomplete_fields = ('evaluacion', 'criterio')
