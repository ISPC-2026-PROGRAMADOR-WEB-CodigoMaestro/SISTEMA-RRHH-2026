"""Vistas de vacaciones y licencias."""
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import SaldoVacaciones, SolicitudLicencia, TipoLicencia
from .serializers import (
    SaldoVacacionesSerializer,
    SolicitudLicenciaSerializer,
    TipoLicenciaSerializer,
)


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

    def perform_create(self, serializer):
        serializer.save(solicitado_por=self.request.user)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        solicitud = self.get_object()
        solicitud.estado = SolicitudLicencia.Estado.APROBADA
        solicitud.revisado_por = request.user
        solicitud.fecha_revision = timezone.now()
        solicitud.observacion_revision = request.data.get('observacion', '')
        solicitud.save()
        return Response(SolicitudLicenciaSerializer(solicitud).data)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        solicitud = self.get_object()
        solicitud.estado = SolicitudLicencia.Estado.RECHAZADA
        solicitud.revisado_por = request.user
        solicitud.fecha_revision = timezone.now()
        solicitud.observacion_revision = request.data.get('observacion', '')
        solicitud.save()
        return Response(SolicitudLicenciaSerializer(solicitud).data)

