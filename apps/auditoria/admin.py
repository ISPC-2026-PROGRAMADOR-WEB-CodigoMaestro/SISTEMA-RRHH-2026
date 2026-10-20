from django.contrib import admin
from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'usuario', 'accion', 'modelo', 'objeto_id', 'ip')
    list_filter = ('accion', 'modelo')
    search_fields = ('usuario__username', 'descripcion', 'modelo', 'objeto_id')
    readonly_fields = (
        'usuario', 'fecha_hora', 'accion', 'modelo', 'objeto_id',
        'descripcion', 'datos_anteriores', 'datos_nuevos', 'ip', 'user_agent', 'ruta',
    )
    date_hierarchy = 'fecha_hora'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
