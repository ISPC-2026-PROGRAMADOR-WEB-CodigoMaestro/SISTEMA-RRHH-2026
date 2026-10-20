from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError

from .models import Sancion
from .services import transicionar_sancion


@admin.register(Sancion)
class SancionAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo', 'fecha_hecho', 'estado', 'responsable')
    list_filter = ('tipo', 'estado')
    search_fields = ('empleado__legajo', 'empleado__apellido', 'descripcion')
    autocomplete_fields = ('empleado', 'responsable')
    date_hierarchy = 'fecha_hecho'
    readonly_fields = (
        'estado', 'fecha_registro', 'fecha_actualizacion',
        'fecha_notificacion', 'fecha_aplicacion', 'fecha_apelacion',
    )
    actions = (
        'notificar_seleccionadas', 'aplicar_seleccionadas',
        'apelar_seleccionadas', 'resolver_apelaciones',
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.estado != Sancion.Estado.PROPUESTA:
            readonly.extend([
                'empleado', 'fecha_hecho', 'tipo', 'descripcion',
                'normativa_incumplida', 'medida_adoptada', 'dias_suspension',
                'documentacion',
            ])
        return readonly

    def _transicionar(self, request, queryset, accion):
        actualizadas = 0
        for sancion in queryset:
            try:
                transicionar_sancion(sancion.pk, accion, request.user)
            except (PermissionDenied, ValidationError) as exc:
                errors = (
                    [error for field_errors in exc.message_dict.values() for error in field_errors]
                    if hasattr(exc, 'message_dict') else getattr(exc, 'messages', [str(exc)])
                )
                self.message_user(request, f'{sancion}: {"; ".join(str(error) for error in errors)}', level='error')
            else:
                actualizadas += 1
        if actualizadas:
            self.message_user(request, f'{actualizadas} sanción(es) actualizadas.')

    @admin.action(description='Notificar sanciones propuestas')
    def notificar_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, 'notificar')

    @admin.action(description='Aplicar sanciones notificadas')
    def aplicar_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, 'aplicar')

    @admin.action(description='Registrar apelación de las sanciones seleccionadas')
    def apelar_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, 'apelar')

    @admin.action(description='Resolver apelaciones aplicando la sanción')
    def resolver_apelaciones(self, request, queryset):
        self._transicionar(request, queryset, 'resolver_apelacion')
