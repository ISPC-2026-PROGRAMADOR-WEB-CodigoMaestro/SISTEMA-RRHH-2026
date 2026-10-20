"""Rutas web para fichaje e importación de asistencia."""
from django.urls import path

from . import web_views

app_name = 'asistencia'

urlpatterns = [
    path('fichar/', web_views.fichar, name='fichar'),
    path('cerrar-hoy/', web_views.cerrar_hoy, name='cerrar_hoy'),
    path('importar/', web_views.importar, name='importar'),
    path('ejemplo.csv', web_views.ejemplo_csv, name='ejemplo_csv'),
]
