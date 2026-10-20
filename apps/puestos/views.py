"""Vistas de puestos, cargos y planta funcional."""
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import Designacion, Puesto
from .serializers import DesignacionSerializer, PuestoSerializer


class PuestoViewSet(viewsets.ModelViewSet):
    queryset = Puesto.objects.select_related('unidad').prefetch_related('designaciones')
    serializer_class = PuestoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['unidad', 'nivel_autoridad', 'activo']
    search_fields = ['codigo', 'denominacion', 'objetivo_general']
    ordering_fields = ['denominacion', 'codigo']

    @action(detail=False, methods=['get'])
    def planta_funcional(self, request):
        """Resumen de cargos previstos, ocupados y vacantes por puesto/área."""
        data = []
        for p in self.get_queryset().filter(activo=True):
            data.append({
                'puesto_id': p.id,
                'codigo': p.codigo,
                'denominacion': p.denominacion,
                'unidad': p.unidad.nombre if p.unidad else None,
                'previstos': p.cantidad_prevista,
                'ocupados': p.cantidad_ocupados,
                'vacantes': p.cantidad_vacantes,
            })
        return Response(data)


class DesignacionViewSet(viewsets.ModelViewSet):
    queryset = Designacion.objects.select_related(
        'empleado', 'puesto', 'superior_jerarquico'
    )
    serializer_class = DesignacionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['activa', 'empleado', 'puesto', 'modalidad_contractual', 'jornada']
    search_fields = ['empleado__legajo', 'empleado__apellido', 'puesto__denominacion']
    ordering_fields = ['fecha_inicio']

