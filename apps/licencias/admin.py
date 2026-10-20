from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import TipoLicencia, SaldoVacaciones, SolicitudLicencia
from .services import aprobar_solicitud, cancelar_solicitud, rechazar_solicitud


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
    actions = ('aprobar_seleccionadas', 'rechazar_seleccionadas', 'cancelar_seleccionadas')

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly = [
            'estado', 'dias_solicitados', 'dias_descontados',
            'solicitado_por', 'revisado_por', 'fecha_revision',
        ]
        if obj and obj.estado not in (
            SolicitudLicencia.Estado.PENDIENTE,
            SolicitudLicencia.Estado.BORRADOR,
        ):
            readonly.extend(['empleado', 'tipo_licencia', 'fecha_inicio', 'fecha_fin', 'motivo'])
        return readonly

    def _transicionar(self, request, queryset, servicio, accion):
        actualizadas = 0
        for solicitud in queryset:
            try:
                servicio(solicitud.pk, request.user)
            except ValidationError as exc:
                errors = (
                    [error for field_errors in exc.message_dict.values() for error in field_errors]
                    if hasattr(exc, 'message_dict') else exc.messages
                )
                self.message_user(
                    request,
                    f'{solicitud}: {"; ".join(str(error) for error in errors)}',
                    level='error',
                )
            else:
                actualizadas += 1
        if actualizadas:
            self.message_user(request, f'{actualizadas} solicitud(es) {accion}.')

    @admin.action(description='Aprobar solicitudes pendientes')
    def aprobar_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, aprobar_solicitud, 'aprobadas')

    @admin.action(description='Rechazar solicitudes pendientes')
    def rechazar_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, rechazar_solicitud, 'rechazadas')

    @admin.action(description='Cancelar solicitudes pendientes o aprobadas')
    def cancelar_seleccionadas(self, request, queryset):
        self._transicionar(request, queryset, cancelar_solicitud, 'canceladas')
