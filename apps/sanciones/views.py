"""Vistas de sanciones disciplinarias."""
from rest_framework import permissions, viewsets

from apps.accounts.permissions import OperarPersonal

from .models import Sancion
from .serializers import SancionSerializer


class SancionViewSet(viewsets.ModelViewSet):
    queryset = Sancion.objects.select_related('empleado', 'responsable')
    serializer_class = SancionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['tipo', 'estado', 'empleado']
    search_fields = ['empleado__legajo', 'empleado__apellido', 'descripcion']
    ordering_fields = ['fecha_hecho', 'fecha_registro']
    ordering = ['-fecha_hecho']

    def perform_create(self, serializer):
        serializer.save(responsable=self.request.user)

