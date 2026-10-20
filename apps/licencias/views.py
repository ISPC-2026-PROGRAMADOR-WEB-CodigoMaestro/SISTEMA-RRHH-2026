"""Vistas de vacaciones y licencias."""
from django.core.exceptions import ValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import SaldoVacaciones, SolicitudLicencia, TipoLicencia
from .serializers import (
    SaldoVacacionesSerializer,
    SolicitudLicenciaSerializer,
    TipoLicenciaSerializer,
)
from .services import aprobar_solicitud, cancelar_solicitud, rechazar_solicitud


class TipoLicenciaViewSet(viewsets.ModelViewSet):
    queryset = TipoLicencia.objects.all()
    serializer_class = TipoLicenciaSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['activo', 'requiere_aprobacion', 'descuenta_vacaciones']
    search_fields = ['codigo', 'nombre']


class SaldoVacacionesViewSet(viewsets.ModelViewSet):
    queryset = SaldoVacaciones.objects.select_related('empleado')
    serializer_class = SaldoVacacionesSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['empleado', 'anio']
    search_fields = ['empleado__legajo', 'empleado__apellido']
    ordering_fields = ['anio']


class SolicitudLicenciaViewSet(viewsets.ModelViewSet):
    queryset = SolicitudLicencia.objects.select_related(
        'empleado', 'tipo_licencia', 'solicitado_por', 'revisado_por'
    )
    serializer_class = SolicitudLicenciaSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['estado', 'tipo_licencia', 'empleado']
    search_fields = ['empleado__legajo', 'empleado__apellido', 'motivo']
    ordering_fields = ['fecha_inicio', 'fecha_solicitud']
    ordering = ['-fecha_solicitud']
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def perform_create(self, serializer):
        serializer.save(solicitado_por=self.request.user)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        try:
            solicitud = aprobar_solicitud(
                self.get_object().pk,
                request.user,
                request.data.get('observacion', ''),
            )
        except ValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SolicitudLicenciaSerializer(solicitud).data)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        try:
            solicitud = rechazar_solicitud(
                self.get_object().pk,
                request.user,
                request.data.get('observacion', ''),
            )
        except ValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SolicitudLicenciaSerializer(solicitud).data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        try:
            solicitud = cancelar_solicitud(
                self.get_object().pk,
                request.user,
                request.data.get('observacion', ''),
            )
        except ValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SolicitudLicenciaSerializer(solicitud).data)
