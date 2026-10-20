from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Incidencia, ComentarioIncidencia
from .services import cambiar_estado_incidencia


class ComentarioIncidenciaInline(admin.TabularInline):
    model = ComentarioIncidencia
    extra = 0
    readonly_fields = ('fecha',)


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'titulo', 'categoria', 'prioridad', 'estado', 'responsable', 'fecha_creacion')
    list_filter = ('categoria', 'prioridad', 'estado')
    search_fields = ('numero', 'titulo', 'descripcion', 'empleado__legajo')
    autocomplete_fields = ('empleado', 'unidad', 'responsable', 'creado_por')
    inlines = [ComentarioIncidenciaInline]
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ('numero', 'fecha_creacion', 'estado', 'fecha_resolucion')
    actions = (
        'asignar', 'analizar', 'solicitar_documentacion',
        'resolver', 'cerrar', 'reabrir',
    )

    def _cambiar_estado(self, request, queryset, estado):
        actualizadas = 0
        for incidencia in queryset:
            try:
                cambiar_estado_incidencia(incidencia.pk, estado)
            except ValidationError as exc:
                errors = (
                    [error for field_errors in exc.message_dict.values() for error in field_errors]
                    if hasattr(exc, 'message_dict') else exc.messages
                )
                self.message_user(
                    request,
                    f'{incidencia}: {"; ".join(str(error) for error in errors)}',
                    level='error',
                )
            else:
                actualizadas += 1
        if actualizadas:
            self.message_user(request, f'{actualizadas} incidencia(s) actualizadas.')

    @admin.action(description='Pasar a asignada')
    def asignar(self, request, queryset):
        self._cambiar_estado(request, queryset, Incidencia.Estado.ASIGNADA)

    @admin.action(description='Pasar a análisis')
    def analizar(self, request, queryset):
        self._cambiar_estado(request, queryset, Incidencia.Estado.EN_ANALISIS)

    @admin.action(description='Solicitar documentación')
    def solicitar_documentacion(self, request, queryset):
        self._cambiar_estado(request, queryset, Incidencia.Estado.PENDIENTE_DOC)

    @admin.action(description='Marcar como resuelta')
    def resolver(self, request, queryset):
        self._cambiar_estado(request, queryset, Incidencia.Estado.RESUELTA)

    @admin.action(description='Cerrar incidencias resueltas')
    def cerrar(self, request, queryset):
        self._cambiar_estado(request, queryset, Incidencia.Estado.CERRADA)

    @admin.action(description='Reabrir para análisis')
    def reabrir(self, request, queryset):
        self._cambiar_estado(request, queryset, Incidencia.Estado.EN_ANALISIS)


@admin.register(ComentarioIncidencia)
class ComentarioIncidenciaAdmin(admin.ModelAdmin):
    list_display = ('incidencia', 'usuario', 'es_accion', 'fecha')
    list_filter = ('es_accion',)
    search_fields = ('incidencia__numero', 'comentario')
    autocomplete_fields = ('incidencia', 'usuario')
