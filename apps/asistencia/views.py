"""Vistas de control de asistencia."""
from django.db.models import Count, Q, Sum
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import RegistroAsistencia
from .serializers import RegistroAsistenciaSerializer


class RegistroAsistenciaViewSet(viewsets.ModelViewSet):
    queryset = RegistroAsistencia.objects.select_related('empleado', 'cargado_por')
    serializer_class = RegistroAsistenciaSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['empleado', 'tipo', 'justificado', 'fecha']
    search_fields = ['empleado__legajo', 'empleado__apellido']
    ordering_fields = ['fecha', 'minutos_tardanza', 'minutos_extra']
    ordering = ['-fecha']

    def perform_create(self, serializer):
        serializer.save(cargado_por=self.request.user)

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Resumen de ausentismo por empleado (para informes)."""
        qs = self.filter_queryset(self.get_queryset())
        resumen = (
            qs.values('empleado__legajo', 'empleado__apellido', 'empleado__nombre')
            .annotate(
                total_registros=Count('id'),
                ausencias=Count('id', filter=Q(tipo=RegistroAsistencia.Tipo.AUSENTE)),
                tardanzas=Count('id', filter=Q(tipo=RegistroAsistencia.Tipo.TARDANZA)),
                minutos_tardanza=Sum('minutos_tardanza'),
                minutos_extra=Sum('minutos_extra'),
            )
            .order_by('empleado__apellido')
        )
        return Response(list(resumen))

