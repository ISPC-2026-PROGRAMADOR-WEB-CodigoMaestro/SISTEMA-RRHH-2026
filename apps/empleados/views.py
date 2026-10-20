"""Vistas de empleados, legajo digital e historial laboral."""
from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import CategoriaDocumento, DocumentoLegajo, Empleado, HistorialLaboral
from .serializers import (
    CategoriaDocumentoSerializer,
    DocumentoLegajoSerializer,
    EmpleadoSerializer,
    HistorialLaboralSerializer,
)


class EmpleadoViewSet(viewsets.ModelViewSet):
    queryset = Empleado.objects.select_related('unidad', 'usuario')
    serializer_class = EmpleadoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['estado', 'unidad', 'tipo_documento', 'genero']
    search_fields = ['legajo', 'apellido', 'nombre', 'numero_documento', 'cuil', 'email']
    ordering_fields = ['apellido', 'legajo', 'fecha_ingreso']
    ordering = ['apellido', 'nombre']

    @action(detail=True, methods=['get'])
    def legajo(self, request, pk=None):
        """Devuelve el legajo digital completo: documentos + historial."""
        empleado = self.get_object()
        documentos = DocumentoLegajoSerializer(
            empleado.documentos.select_related('categoria'), many=True
        ).data
        historial = HistorialLaboralSerializer(
            empleado.historial.all(), many=True
        ).data
        return Response({
            'empleado': EmpleadoSerializer(empleado).data,
            'documentos': documentos,
            'historial': historial,
        })

    @action(detail=False, methods=['get'])
    def con_documentacion_vencida(self, request):
        """Empleados con documentación vencida o próxima a vencer."""
        hoy = timezone.localdate()
        docs = (
            DocumentoLegajo.objects.filter(
                activo=True, fecha_vencimiento__isnull=False,
                fecha_vencimiento__lte=hoy + timedelta(days=30),
            )
            .select_related('empleado', 'categoria')
        )
        return Response(DocumentoLegajoSerializer(docs, many=True).data)


class CategoriaDocumentoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaDocumento.objects.all()
    serializer_class = CategoriaDocumentoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['requiere_vencimiento', 'sensible', 'activa']
    search_fields = ['nombre']


class DocumentoLegajoViewSet(viewsets.ModelViewSet):
    queryset = DocumentoLegajo.objects.select_related('empleado', 'categoria', 'cargado_por')
    serializer_class = DocumentoLegajoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['empleado', 'categoria', 'activo']
    search_fields = ['titulo', 'empleado__legajo', 'empleado__apellido']
    ordering_fields = ['fecha_carga', 'fecha_vencimiento']

    def perform_create(self, serializer):
        serializer.save(cargado_por=self.request.user)


class HistorialLaboralViewSet(viewsets.ModelViewSet):
    """CRUD del historial laboral (sin eliminación: trazabilidad)."""

    queryset = HistorialLaboral.objects.select_related('empleado', 'usuario')
    serializer_class = HistorialLaboralSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    http_method_names = ['get', 'post', 'head', 'options']
    filterset_fields = ['empleado', 'tipo_movimiento']
    search_fields = ['empleado__legajo', 'descripcion']
    ordering_fields = ['fecha']

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

