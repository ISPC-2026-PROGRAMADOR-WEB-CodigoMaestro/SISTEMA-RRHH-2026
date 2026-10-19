"""Vistas de gestión de incidencias."""
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import ComentarioIncidencia, Incidencia
from .serializers import ComentarioIncidenciaSerializer, IncidenciaSerializer


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
        texto = request.data.get('comentario', '').strip()
        if not texto:
            return Response(
                {'comentario': 'El comentario no puede estar vacío.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        comentario = ComentarioIncidencia.objects.create(
            incidencia=incidencia,
            usuario=request.user,
            comentario=texto,
            es_accion=bool(request.data.get('es_accion', False)),
        )
        return Response(ComentarioIncidenciaSerializer(comentario).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """Cambia el estado de la incidencia (y registra resolución si aplica)."""
        incidencia = self.get_object()
        nuevo_estado = request.data.get('estado')
        estados_validos = [e[0] for e in Incidencia.Estado.choices]
        if nuevo_estado not in estados_validos:
            return Response(
                {'estado': f'Estado inválido. Opciones: {estados_validos}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        incidencia.estado = nuevo_estado
        if nuevo_estado in (Incidencia.Estado.RESUELTA, Incidencia.Estado.CERRADA):
            incidencia.fecha_resolucion = timezone.now()
        incidencia.save()
        return Response(IncidenciaSerializer(incidencia).data)

    @action(detail=True, methods=['post'])
    def reasignar(self, request, pk=None):
        """Reasigna la incidencia a otro usuario responsable."""
        incidencia = self.get_object()
        responsable_id = request.data.get('responsable')
        if not responsable_id:
            return Response(
                {'responsable': 'Debe indicar el usuario responsable.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        incidencia.responsable_id = responsable_id
        if incidencia.estado == Incidencia.Estado.ABIERTA:
            incidencia.estado = Incidencia.Estado.ASIGNADA
        incidencia.save()
        return Response(IncidenciaSerializer(incidencia).data)

