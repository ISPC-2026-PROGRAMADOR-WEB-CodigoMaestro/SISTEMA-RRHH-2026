
"""Rutas de la app reclutamiento."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EntrevistaViewSet,
    PostulacionViewSet,
    PostulanteViewSet,
    VacanteViewSet,
)

router = DefaultRouter()
router.register('vacantes', VacanteViewSet, basename='vacante')
router.register('postulantes', PostulanteViewSet, basename='postulante')
router.register('postulaciones', PostulacionViewSet, basename='postulacion')
router.register('entrevistas', EntrevistaViewSet, basename='entrevista')

urlpatterns = [
    path('', include(router.urls)),
]
