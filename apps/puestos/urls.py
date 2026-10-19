"""Rutas de la app puestos."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DesignacionViewSet, PuestoViewSet

router = DefaultRouter()
router.register('puestos', PuestoViewSet, basename='puesto')
router.register('designaciones', DesignacionViewSet, basename='designacion')

urlpatterns = [
    path('', include(router.urls)),
]
