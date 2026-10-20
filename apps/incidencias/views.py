"""Vistas de gestión de incidencias."""
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import ComentarioIncidencia, Incidencia
from .serializers import (
    ComentarioIncidenciaSerializer,
    EntradaComentarioSerializer,
    IncidenciaSerializer,
    ReasignarIncidenciaSerializer,
)
from .services import cambiar_estado_incidencia


class IncidenciaViewSet(viewsets.ModelViewSet):
    queryset = Incidencia.objects.select_related(
        'empleado', 'unidad', 'responsable', 'creado_por'
    ).prefetch_related('comentarios__usuario')
    serializer_class = IncidenciaSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['categoria', 'prioridad', 'estado', 'empleado', 'unidad', 'responsable']
    search_fields = ['numero', 'titulo', 'descripcion', 'empleado__legajo']
    ordering_fields = ['fecha_creacion', 'prioridad', 'estado']
    ordering = ['-fecha_creacion']

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    @action(detail=True, methods=['post'])
    def comentar(self, request, pk=None):
        """Agrega un comentario o acción a la incidencia."""
        incidencia = self.get_object()
        entrada = EntradaComentarioSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        texto = entrada.validated_data['comentario'].strip()
        if not texto:
            return Response({'comentario': 'El comentario no puede estar vacío.'},
                            status=status.HTTP_400_BAD_REQUEST)
        comentario = ComentarioIncidencia.objects.create(
            incidencia=incidencia,
            usuario=request.user,
            comentario=texto,
            es_accion=entrada.validated_data['es_accion'],
        )
        return Response(ComentarioIncidenciaSerializer(comentario).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """Cambia el estado de la incidencia (y registra resolución si aplica)."""
        incidencia = self.get_object()
        nuevo_estado = request.data.get('estado')
        try:
            incidencia = cambiar_estado_incidencia(incidencia.pk, nuevo_estado)
        except ValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(IncidenciaSerializer(incidencia).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reasignar(self, request, pk=None):
        """Reasigna la incidencia a otro usuario responsable."""
        incidencia = self.get_object()
        entrada = ReasignarIncidenciaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        user = entrada.validated_data['responsable']
        incidencia.responsable = user
        incidencia.save(update_fields=['responsable', 'fecha_actualizacion'])
        if incidencia.estado == Incidencia.Estado.ABIERTA:
            incidencia = cambiar_estado_incidencia(
                incidencia.pk,
                Incidencia.Estado.ASIGNADA,
            )
        return Response(IncidenciaSerializer(incidencia).data)
