"""Rutas de la app asistencia."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RegistroAsistenciaViewSet

router = DefaultRouter()
router.register('registros', RegistroAsistenciaViewSet, basename='registro-asistencia')

urlpatterns = [
    path('', include(router.urls)),
]
