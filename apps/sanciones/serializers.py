"""Serializers de sanciones disciplinarias."""
from rest_framework import serializers

from .models import Sancion


class SancionSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Sancion
        fields = [
            'id', 'empleado', 'empleado_nombre', 'fecha_hecho', 'tipo',
            'tipo_display', 'descripcion', 'normativa_incumplida',
            'medida_adoptada', 'dias_suspension', 'descargo_trabajador',
            'estado', 'estado_display', 'documentacion', 'responsable',
            'fecha_registro', 'fecha_actualizacion', 'observaciones',
        ]
        read_only_fields = ['fecha_registro', 'fecha_actualizacion', 'responsable']
