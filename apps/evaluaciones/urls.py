"""Rutas de la app evaluaciones."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CriterioEvaluacionViewSet,
    EvaluacionDesempenoViewSet,
    PeriodoEvaluacionViewSet,
)

router = DefaultRouter()
router.register('periodos', PeriodoEvaluacionViewSet, basename='periodo')
router.register('criterios', CriterioEvaluacionViewSet, basename='criterio')
router.register('evaluaciones', EvaluacionDesempenoViewSet, basename='evaluacion')

urlpatterns = [
    path('', include(router.urls)),
]
