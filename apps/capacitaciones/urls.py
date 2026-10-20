"""Rutas de la app capacitaciones."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AsistenciaCapacitacionViewSet,
    CertificadoViewSet,
    CursoViewSet,
    InscripcionViewSet,
)

router = DefaultRouter()
router.register('cursos', CursoViewSet, basename='curso')
router.register('inscripciones', InscripcionViewSet, basename='inscripcion')
router.register('asistencias', AsistenciaCapacitacionViewSet, basename='asistencia-capacitacion')
router.register('certificados', CertificadoViewSet, basename='certificado-capacitacion')

urlpatterns = [path('', include(router.urls))]
