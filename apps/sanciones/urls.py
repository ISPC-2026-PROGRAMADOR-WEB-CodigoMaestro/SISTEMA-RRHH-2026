"""Rutas de la app sanciones."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SancionViewSet

router = DefaultRouter()
router.register('sanciones', SancionViewSet, basename='sancion')

urlpatterns = [
    path('', include(router.urls)),
]
