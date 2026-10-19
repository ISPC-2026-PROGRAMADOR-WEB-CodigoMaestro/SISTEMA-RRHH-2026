"""Vistas de evaluación de desempeño."""
from rest_framework import permissions, viewsets

from apps.accounts.permissions import OperarPersonal

from .models import CriterioEvaluacion, EvaluacionDesempeno, PeriodoEvaluacion
from .serializers import (
    CriterioEvaluacionSerializer,
    EvaluacionDesempenoSerializer,
    PeriodoEvaluacionSerializer,
)


class PeriodoEvaluacionViewSet(viewsets.ModelViewSet):
    queryset = PeriodoEvaluacion.objects.all()
    serializer_class = PeriodoEvaluacionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['activo']
    search_fields = ['nombre']
    ordering_fields = ['fecha_inicio']


class CriterioEvaluacionViewSet(viewsets.ModelViewSet):
    queryset = CriterioEvaluacion.objects.all()
    serializer_class = CriterioEvaluacionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['activo']
    search_fields = ['nombre']


class EvaluacionDesempenoViewSet(viewsets.ModelViewSet):
    queryset = EvaluacionDesempeno.objects.select_related(
        'empleado', 'periodo', 'evaluador'
    ).prefetch_related('detalles__criterio')
    serializer_class = EvaluacionDesempenoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['estado', 'periodo', 'empleado']
    search_fields = ['empleado__legajo', 'empleado__apellido']
    ordering_fields = ['fecha_evaluacion', 'calificacion_general']
    ordering = ['-fecha_evaluacion']

    def perform_create(self, serializer):
        serializer.save(evaluador=self.request.user)

