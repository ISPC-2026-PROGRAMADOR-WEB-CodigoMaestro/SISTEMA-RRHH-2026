"""Vistas de cuentas: usuarios, grupos, perfil y contraseña."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import EsGerenteRRHH
from .serializers import (
    ChangePasswordSerializer,
    GrupoSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class PerfilActualView(RetrieveUpdateAPIView):
    """Devuelve y permite actualizar los datos del usuario autenticado."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CambiarPasswordView(APIView):
    """Permite al usuario autenticado cambiar su contraseña."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses={200: None})
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Contraseña actualizada correctamente.'},
            status=status.HTTP_200_OK,
        )


class UsuarioViewSet(viewsets.ModelViewSet):
    """CRUD de usuarios del sistema (solo Gerente de RRHH)."""

    queryset = User.objects.all().select_related('perfil').prefetch_related('groups')
    permission_classes = [permissions.IsAuthenticated, EsGerenteRRHH]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'date_joined', 'last_login']
    filterset_fields = ['is_active', 'is_staff']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return UserCreateSerializer
        return UserSerializer


class GrupoViewSet(viewsets.ModelViewSet):
    """CRUD de grupos/roles del sistema (solo Gerente de RRHH)."""

    queryset = Group.objects.all().prefetch_related('permissions')
    serializer_class = GrupoSerializer
    permission_classes = [permissions.IsAuthenticated, EsGerenteRRHH]
    search_fields = ['name']

