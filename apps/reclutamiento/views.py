
"""Vistas de vacantes, postulantes, postulaciones y entrevistas."""
from rest_framework import permissions, viewsets

from apps.accounts.permissions import OperarPersonal

from .models import Entrevista, Postulacion, Postulante, Vacante
from .serializers import (
    EntrevistaSerializer,
    PostulacionSerializer,
    PostulanteSerializer,
    VacanteSerializer,
)


class VacanteViewSet(viewsets.ModelViewSet):
    queryset = Vacante.objects.select_related('puesto')
    serializer_class = VacanteSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['puesto', 'estado']
    search_fields = ['titulo', 'descripcion', 'puesto__denominacion']
    ordering_fields = ['fecha_publicacion', 'titulo']


class PostulanteViewSet(viewsets.ModelViewSet):
    queryset = Postulante.objects.all()
    serializer_class = PostulanteSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    search_fields = ['apellido', 'nombre', 'numero_documento', 'email']
    ordering_fields = ['apellido', 'fecha_registro']


class PostulacionViewSet(viewsets.ModelViewSet):
    queryset = Postulacion.objects.select_related(
        'postulante', 'vacante'
    )
    serializer_class = PostulacionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['vacante', 'postulante', 'estado']
    search_fields = [
        'postulante__apellido',
        'postulante__nombre',
        'vacante__titulo',
    ]
    ordering_fields = ['fecha_postulacion']


class EntrevistaViewSet(viewsets.ModelViewSet):
    queryset = Entrevista.objects.select_related(
        'postulacion__postulante',
        'postulacion__vacante',
    )
    serializer_class = EntrevistaSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['postulacion', 'resultado']
    search_fields = [
        'postulacion__postulante__apellido',
        'entrevistador',
    ]
    ordering_fields = ['fecha']
