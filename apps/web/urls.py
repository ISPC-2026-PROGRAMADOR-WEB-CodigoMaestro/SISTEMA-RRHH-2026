"""Rutas del dashboard web."""
from django.urls import path

from . import views

app_name = 'web'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reportes/', views.reportes_view, name='reportes'),
    path('incidencias/<int:pk>/', views.incidencia_detalle, name='incidencia_detalle'),
    path('m/<slug:slug>/', views.modulo_list, name='modulo'),
    path('m/<slug:slug>/<int:pk>/editar/', views.modulo_editar, name='modulo_editar'),
    path('m/<slug:slug>/<int:pk>/eliminar/', views.modulo_eliminar, name='modulo_eliminar'),
    path('usuarios/', views.usuarios_listar, name='usuarios'),
    path('usuarios/crear/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:pk>/eliminar/', views.usuario_eliminar, name='usuario_eliminar'),
]
