from django.contrib import admin
from .models import Incidencia, ComentarioIncidencia


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
    readonly_fields = ('numero', 'fecha_creacion')
    inlines = [ComentarioIncidenciaInline]
    date_hierarchy = 'fecha_creacion'


@admin.register(ComentarioIncidencia)
class ComentarioIncidenciaAdmin(admin.ModelAdmin):
    list_display = ('incidencia', 'usuario', 'es_accion', 'fecha')
    list_filter = ('es_accion',)
    search_fields = ('incidencia__numero', 'comentario')
    autocomplete_fields = ('incidencia', 'usuario')
