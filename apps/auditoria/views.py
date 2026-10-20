"""Vistas de la bitácora de auditoría (solo lectura)."""
from rest_framework import permissions, viewsets

from apps.accounts.permissions import EsGerenteRRHH

from .models import RegistroAuditoria
from .serializers import RegistroAuditoriaSerializer


class RegistroAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta de la bitácora de auditoría (solo Gerente de RRHH)."""

    queryset = RegistroAuditoria.objects.all().select_related('usuario')
    serializer_class = RegistroAuditoriaSerializer
    permission_classes = [permissions.IsAuthenticated, EsGerenteRRHH]
    filterset_fields = ['accion', 'modelo', 'usuario']
    search_fields = ['descripcion', 'modelo', 'objeto_id', 'usuario__username']
    ordering_fields = ['fecha_hora']
    ordering = ['-fecha_hora']

