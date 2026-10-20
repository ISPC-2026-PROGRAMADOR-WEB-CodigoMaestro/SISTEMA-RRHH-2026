"""Vistas de evaluación de desempeño."""
from django.core.exceptions import ValidationError
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.permissions import OperarPersonal

from .models import CriterioEvaluacion, EvaluacionDesempeno, PeriodoEvaluacion
from .serializers import (
    CriterioEvaluacionSerializer,
    EvaluacionDesempenoSerializer,
    PeriodoEvaluacionSerializer,
)
from .services import cambiar_estado_evaluacion, comparar_con_periodo_anterior


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

    @action(detail=True, methods=['post'])
    def iniciar(self, request, pk=None):
        return self._transicionar(request, 'iniciar')

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        return self._transicionar(request, 'finalizar')

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        return self._transicionar(request, 'anular')

    def _transicionar(self, request, accion):
        try:
            evaluacion = cambiar_estado_evaluacion(self.get_object().pk, accion, request.user)
        except ValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EvaluacionDesempenoSerializer(evaluacion).data)

    @action(detail=True, methods=['get'])
    def comparar_periodo_anterior(self, request, pk=None):
        try:
            resultado = comparar_con_periodo_anterior(self.get_object())
        except ValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        if resultado is None:
            return Response(
                {'detail': 'No hay una evaluación finalizada de un período anterior.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(resultado)
