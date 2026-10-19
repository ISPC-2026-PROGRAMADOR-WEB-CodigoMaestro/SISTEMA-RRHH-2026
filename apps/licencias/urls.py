"""Rutas de la app licencias."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    SaldoVacacionesViewSet,
    SolicitudLicenciaViewSet,
    TipoLicenciaViewSet,
)

router = DefaultRouter()
router.register('tipos', TipoLicenciaViewSet, basename='tipo-licencia')
router.register('saldos', SaldoVacacionesViewSet, basename='saldo-vacaciones')
router.register('solicitudes', SolicitudLicenciaViewSet, basename='solicitud-licencia')

urlpatterns = [
    path('', include(router.urls)),
]
