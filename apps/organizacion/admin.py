from django.contrib import admin
from .models import UnidadOrganizacional


@admin.register(UnidadOrganizacional)
class UnidadOrganizacionalAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'parent', 'activa', 'orden')
    list_filter = ('tipo', 'activa')
    search_fields = ('codigo', 'nombre')
    autocomplete_fields = ('parent',)
