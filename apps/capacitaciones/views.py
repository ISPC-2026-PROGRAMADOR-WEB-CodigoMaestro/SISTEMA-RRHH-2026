"""API de cursos, inscripciones, asistencia y certificados."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import AsistenciaCapacitacion, Certificado, Curso, Inscripcion
from .serializers import (
    AsistenciaCapacitacionSerializer,
    CertificadoSerializer,
    CursoSerializer,
    InscripcionSerializer,
)
from .services import emitir_certificado


class CursoViewSet(viewsets.ModelViewSet):
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['activo', 'fecha_inicio', 'fecha_fin']
    search_fields = ['nombre', 'instructor', 'descripcion']
    ordering_fields = ['nombre', 'fecha_inicio', 'fecha_fin']


class InscripcionViewSet(viewsets.ModelViewSet):
    queryset = Inscripcion.objects.select_related('curso', 'empleado')
    serializer_class = InscripcionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['curso', 'empleado', 'estado']
    search_fields = ['curso__nombre', 'empleado__legajo', 'empleado__apellido']
    ordering_fields = ['fecha_inscripcion', 'estado']
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def perform_update(self, serializer):
        serializer.save()

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def emitir_certificado(self, request, pk=None):
        archivo = request.FILES.get('archivo')
        if archivo is None:
            return Response(
                {'archivo': 'Adjunta el archivo del certificado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            certificado = emitir_certificado(
                self.get_object().pk,
                archivo,
                request.user,
                request.data.get('titulo', ''),
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CertificadoSerializer(certificado).data, status=status.HTTP_201_CREATED)


class AsistenciaCapacitacionViewSet(viewsets.ModelViewSet):
    queryset = AsistenciaCapacitacion.objects.select_related(
        'inscripcion__curso', 'inscripcion__empleado', 'registrada_por'
    )
    serializer_class = AsistenciaCapacitacionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['inscripcion', 'fecha', 'presente']
    search_fields = ['inscripcion__curso__nombre', 'inscripcion__empleado__legajo']
    ordering_fields = ['fecha']

    def perform_create(self, serializer):
        serializer.save(registrada_por=self.request.user)


class CertificadoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Certificado.objects.select_related(
        'inscripcion__empleado', 'inscripcion__curso', 'documento_legajo'
    )
    serializer_class = CertificadoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['inscripcion', 'fecha_emision']
    search_fields = ['inscripcion__curso__nombre', 'inscripcion__empleado__legajo']
    ordering_fields = ['fecha_emision']
