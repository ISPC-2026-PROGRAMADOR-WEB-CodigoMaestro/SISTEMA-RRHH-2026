"""Vistas de estructura organizacional."""
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal

from .models import UnidadOrganizacional
from .serializers import UnidadOrganizacionalSerializer


class UnidadOrganizacionalViewSet(viewsets.ModelViewSet):
    queryset = UnidadOrganizacional.objects.all().select_related('parent')
    serializer_class = UnidadOrganizacionalSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['tipo', 'activa', 'parent']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering_fields = ['orden', 'nombre', 'codigo']

    @action(detail=False, methods=['get'])
    def organigrama(self, request):
        """Devuelve la estructura organizacional como árbol jerárquico."""
        unidades = list(self.get_queryset().filter(activa=True))
        nodos = {
            u.id: {
                'id': u.id, 'codigo': u.codigo, 'nombre': u.nombre,
                'tipo': u.tipo, 'parent': u.parent_id, 'hijos': [],
            }
            for u in unidades
        }
        raices = []
        for u in unidades:
            nodo = nodos[u.id]
            if u.parent_id and u.parent_id in nodos:
                nodos[u.parent_id]['hijos'].append(nodo)
            else:
                raices.append(nodo)
        return Response(raices)

