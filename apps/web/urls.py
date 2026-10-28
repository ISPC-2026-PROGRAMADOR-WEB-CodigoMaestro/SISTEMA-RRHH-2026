"""Rutas del dashboard web."""
from django.urls import path

from . import views

app_name = 'web'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reportes/', views.reportes_view, name='reportes'),
    path('mis-licencias/', views.mis_licencias, name='mis_licencias'),
    path('horarios-laborales/', views.horarios_laborales, name='horarios_laborales'),
    path(
        'horarios-laborales/plantilla/',
        views.plantilla_horarios_laborales,
        name='plantilla_horarios_laborales',
    ),
    path('mis-licencias/<int:pk>/cancelar/', views.cancelar_mi_licencia, name='cancelar_mi_licencia'),
    path(
        'asistencia/empleados/<int:empleado_id>/',
        views.asistencia_empleado_mes,
        name='asistencia_empleado_mes',
    ),
    path('incidencias/<int:pk>/', views.incidencia_detalle, name='incidencia_detalle'),
    path('m/<slug:slug>/', views.modulo_list, name='modulo'),
    path('m/<slug:slug>/<int:pk>/editar/', views.modulo_editar, name='modulo_editar'),
    path('m/<slug:slug>/<int:pk>/eliminar/', views.modulo_eliminar, name='modulo_eliminar'),
    path('usuarios/', views.usuarios_listar, name='usuarios'),
    path('usuarios/crear/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:pk>/eliminar/', views.usuario_eliminar, name='usuario_eliminar'),
]
