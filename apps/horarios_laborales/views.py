from datetime import date

from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError

from apps.accounts.permissions import rol_de

from .models import HorarioDiario
from .permissions import GestionarHorariosOPropioEmpleado
from .serializers import HorarioDiarioSerializer


class HorarioDiarioViewSet(viewsets.ModelViewSet):
    queryset = HorarioDiario.objects.select_related('empleado', 'creado_por')
    serializer_class = HorarioDiarioSerializer
    permission_classes = [permissions.IsAuthenticated, GestionarHorariosOPropioEmpleado]
    filterset_fields = ['empleado', 'fecha', 'es_franco']
    ordering_fields = ['fecha', 'empleado__apellido']
    ordering = ['-fecha']

    def get_queryset(self):
        queryset = super().get_queryset()
        if rol_de(self.request.user) not in ('GERENTE', 'ADMINISTRATIVO', 'LECTURA'):
            queryset = queryset.filter(empleado__usuario=self.request.user)

        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_desde:
            queryset = queryset.filter(fecha__gte=self._parse_date(fecha_desde, 'fecha_desde'))
        if fecha_hasta:
            queryset = queryset.filter(fecha__lte=self._parse_date(fecha_hasta, 'fecha_hasta'))
        return queryset

    @staticmethod
    def _parse_date(value, parameter):
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError({
                parameter: 'La fecha debe tener el formato YYYY-MM-DD.',
            }) from exc

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)
