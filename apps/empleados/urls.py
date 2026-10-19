"""Rutas de la app empleados."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoriaDocumentoViewSet,
    DocumentoLegajoViewSet,
    EmpleadoViewSet,
    HistorialLaboralViewSet,
)

router = DefaultRouter()
router.register('empleados', EmpleadoViewSet, basename='empleado')
router.register('categorias-documento', CategoriaDocumentoViewSet, basename='categoria-documento')
router.register('documentos', DocumentoLegajoViewSet, basename='documento')
router.register('historial', HistorialLaboralViewSet, basename='historial')

urlpatterns = [
    path('', include(router.urls)),
]
