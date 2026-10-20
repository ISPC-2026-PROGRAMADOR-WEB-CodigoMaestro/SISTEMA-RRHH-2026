"""Rutas de la app organizacion."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UnidadOrganizacionalViewSet

router = DefaultRouter()
router.register('unidades', UnidadOrganizacionalViewSet, basename='unidad')

urlpatterns = [
    path('', include(router.urls)),
]
