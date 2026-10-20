from django.contrib import admin
from .models import Puesto, Designacion


class DesignacionInline(admin.TabularInline):
    model = Designacion
    extra = 0
    fields = ('empleado', 'fecha_inicio', 'fecha_fin', 'modalidad_contractual', 'jornada', 'activa')
    autocomplete_fields = ('empleado', 'superior_jerarquico')
    show_change_link = True


@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'denominacion', 'unidad', 'nivel_autoridad', 'cantidad_prevista', 'activo')
    list_filter = ('nivel_autoridad', 'activo', 'unidad')
    search_fields = ('codigo', 'denominacion')
    autocomplete_fields = ('unidad', 'puesto_superior')
    inlines = [DesignacionInline]


@admin.register(Designacion)
class DesignacionAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'puesto', 'fecha_inicio', 'fecha_fin', 'modalidad_contractual', 'activa')
    list_filter = ('activa', 'modalidad_contractual', 'jornada')
    search_fields = ('empleado__legajo', 'empleado__apellido', 'puesto__denominacion')
    autocomplete_fields = ('empleado', 'puesto', 'superior_jerarquico')
