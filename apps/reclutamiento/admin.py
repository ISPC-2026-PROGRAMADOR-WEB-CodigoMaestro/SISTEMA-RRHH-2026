
from django.contrib import admin
from .models import Vacante, Postulante, Postulacion, Entrevista


class EntrevistaInline(admin.TabularInline):
    model = Entrevista
    extra = 0
    fields = ('fecha', 'entrevistador', 'resultado', 'observaciones')
    show_change_link = True


@admin.register(Vacante)
class VacanteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'puesto', 'cantidad_vacantes', 'fecha_publicacion', 'fecha_cierre', 'estado')
    list_filter = ('estado', 'fecha_publicacion')
    search_fields = ('titulo', 'puesto__codigo', 'puesto__denominacion')
    autocomplete_fields = ('puesto',)


@admin.register(Postulante)
class PostulanteAdmin(admin.ModelAdmin):
    list_display = ('apellido', 'nombre', 'numero_documento', 'email', 'telefono', 'fecha_registro')
    search_fields = ('apellido', 'nombre', 'numero_documento', 'email')


@admin.register(Postulacion)
class PostulacionAdmin(admin.ModelAdmin):
    list_display = ('postulante', 'vacante', 'fecha_postulacion', 'estado')
    list_filter = ('estado', 'fecha_postulacion')
    search_fields = ('postulante__apellido', 'postulante__nombre', 'vacante__titulo')
    autocomplete_fields = ('postulante', 'vacante')
    inlines = [EntrevistaInline]


@admin.register(Entrevista)
class EntrevistaAdmin(admin.ModelAdmin):
    list_display = ('postulacion', 'fecha', 'entrevistador', 'resultado')
    list_filter = ('resultado', 'fecha')
    search_fields = ('postulacion__postulante__apellido', 'entrevistador')
    autocomplete_fields = ('postulacion',)
