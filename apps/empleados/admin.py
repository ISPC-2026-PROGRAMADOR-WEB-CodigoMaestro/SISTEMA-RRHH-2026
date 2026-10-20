from django.contrib import admin
from .models import Empleado, CategoriaDocumento, DocumentoLegajo, HistorialLaboral


class DocumentoLegajoInline(admin.TabularInline):
    model = DocumentoLegajo
    extra = 0
    fields = ('categoria', 'titulo', 'archivo', 'fecha_emision', 'fecha_vencimiento', 'activo')
    show_change_link = True


class HistorialLaboralInline(admin.TabularInline):
    model = HistorialLaboral
    extra = 0
    fields = ('fecha', 'tipo_movimiento', 'descripcion', 'usuario')
    readonly_fields = ('fecha', 'tipo_movimiento', 'descripcion', 'usuario')
    can_delete = False
    show_change_link = True


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('legajo', 'apellido', 'nombre', 'numero_documento', 'estado', 'fecha_ingreso', 'unidad')
    list_filter = ('estado', 'unidad', 'fecha_ingreso')
    search_fields = ('legajo', 'apellido', 'nombre', 'numero_documento', 'cuil', 'email')
    autocomplete_fields = ('unidad', 'usuario')
    inlines = [DocumentoLegajoInline, HistorialLaboralInline]
    date_hierarchy = 'fecha_ingreso'


@admin.register(CategoriaDocumento)
class CategoriaDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'requiere_vencimiento', 'dias_alerta_previa', 'sensible', 'activa')
    list_filter = ('requiere_vencimiento', 'sensible', 'activa')
    search_fields = ('nombre',)


@admin.register(DocumentoLegajo)
class DocumentoLegajoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'empleado', 'categoria', 'fecha_vencimiento', 'activo', 'fecha_carga')
    list_filter = ('categoria', 'activo')
    search_fields = ('titulo', 'empleado__legajo', 'empleado__apellido')
    autocomplete_fields = ('empleado', 'categoria', 'cargado_por')


@admin.register(HistorialLaboral)
class HistorialLaboralAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'tipo_movimiento', 'usuario', 'fecha_registro')
    list_filter = ('tipo_movimiento',)
    search_fields = ('empleado__legajo', 'descripcion')
    autocomplete_fields = ('empleado', 'usuario')
    readonly_fields = ('fecha_registro',)

    def has_delete_permission(self, request, obj=None):
        return False
