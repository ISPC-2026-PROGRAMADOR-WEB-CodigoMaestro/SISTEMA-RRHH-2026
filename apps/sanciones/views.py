"""Vistas de sanciones disciplinarias."""
from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.permissions import OperarPersonal

from .models import Sancion
from .serializers import SancionSerializer
from .services import transicionar_sancion


class SancionViewSet(viewsets.ModelViewSet):
    queryset = Sancion.objects.select_related('empleado', 'responsable')
    serializer_class = SancionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['tipo', 'estado', 'empleado']
    search_fields = ['empleado__legajo', 'empleado__apellido', 'descripcion']
    ordering_fields = ['fecha_hecho', 'fecha_registro']
    ordering = ['-fecha_hecho']

    def get_permissions(self):
        if getattr(self, 'action', None) == 'apelar':
            return [permissions.IsAuthenticated()]
        return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        serializer.save(responsable=self.request.user)

    def _transicionar(self, request, accion):
        try:
            sancion = transicionar_sancion(
                self.get_object().pk,
                accion,
                request.user,
                request.data.get('observacion', ''),
            )
        except PermissionDenied as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
            raise DRFPermissionDenied(str(exc)) from exc
        except ValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SancionSerializer(sancion).data)

    @action(detail=True, methods=['post'])
    def notificar(self, request, pk=None):
        return self._transicionar(request, 'notificar')

    @action(detail=True, methods=['post'])
    def aplicar(self, request, pk=None):
        return self._transicionar(request, 'aplicar')

    @action(detail=True, methods=['post'])
    def apelar(self, request, pk=None):
        return self._transicionar(request, 'apelar')

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, OperarPersonal])
    def resolver_apelacion(self, request, pk=None):
        return self._transicionar(request, 'resolver_apelacion')
