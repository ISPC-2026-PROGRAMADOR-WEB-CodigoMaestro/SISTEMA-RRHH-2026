"""Rutas de la app auditoría."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RegistroAuditoriaViewSet

router = DefaultRouter()
router.register('registros', RegistroAuditoriaViewSet, basename='registro-auditoria')

urlpatterns = [
    path('', include(router.urls)),
]
