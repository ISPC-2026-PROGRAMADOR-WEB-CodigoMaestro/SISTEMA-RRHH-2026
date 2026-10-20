"""Rutas de la app asistencia."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AsignacionJornadaViewSet,
    FeriadoViewSet,
    JornadaViewSet,
    MarcacionViewSet,
    RegistroAsistenciaViewSet,
    TurnoViewSet,
)

router = DefaultRouter()
router.register('turnos', TurnoViewSet, basename='turno')
router.register('jornadas', JornadaViewSet, basename='jornada')
router.register('asignaciones-jornada', AsignacionJornadaViewSet, basename='asignacion-jornada')
router.register('feriados', FeriadoViewSet, basename='feriado')
router.register('marcaciones', MarcacionViewSet, basename='marcacion')
router.register('registros', RegistroAsistenciaViewSet, basename='registro-asistencia')

urlpatterns = [
    path('', include(router.urls)),
]
