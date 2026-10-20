from django.contrib import admin

from .models import AsistenciaCapacitacion, Certificado, Curso, Inscripcion


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'instructor', 'activo')
    list_filter = ('activo', 'fecha_inicio')
    search_fields = ('nombre', 'instructor')


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('curso', 'empleado', 'estado', 'fecha_inscripcion')
    list_filter = ('estado', 'curso')
    search_fields = ('curso__nombre', 'empleado__legajo', 'empleado__apellido')
    autocomplete_fields = ('curso', 'empleado')


@admin.register(AsistenciaCapacitacion)
class AsistenciaCapacitacionAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'fecha', 'presente', 'registrada_por')
    list_filter = ('presente', 'fecha')
    search_fields = ('inscripcion__curso__nombre', 'inscripcion__empleado__legajo')
    autocomplete_fields = ('inscripcion', 'registrada_por')


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'fecha_emision', 'documento_legajo')
    readonly_fields = ('inscripcion', 'documento_legajo', 'fecha_emision')
    search_fields = ('inscripcion__curso__nombre', 'inscripcion__empleado__legajo')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
