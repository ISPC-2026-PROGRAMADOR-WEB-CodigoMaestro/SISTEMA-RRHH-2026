"""Serializers de estructura organizacional."""
from rest_framework import serializers

from .models import UnidadOrganizacional


class UnidadOrganizacionalSerializer(serializers.ModelSerializer):
    parent_nombre = serializers.CharField(source='parent.nombre', read_only=True)
    ruta_jerarquica = serializers.CharField(read_only=True)

    class Meta:
        model = UnidadOrganizacional
        fields = [
            'id', 'codigo', 'nombre', 'tipo', 'descripcion', 'parent',
            'parent_nombre', 'activa', 'orden', 'ruta_jerarquica',
            'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']
