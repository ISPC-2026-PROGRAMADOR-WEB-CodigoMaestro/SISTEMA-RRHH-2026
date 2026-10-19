"""Serializers de control de asistencia."""
from rest_framework import serializers

from .models import RegistroAsistencia


class RegistroAsistenciaSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = RegistroAsistencia
        fields = [
            'id', 'empleado', 'empleado_nombre', 'fecha', 'hora_ingreso',
            'hora_egreso', 'tipo', 'tipo_display', 'minutos_tardanza',
            'minutos_extra', 'justificado', 'justificacion', 'observaciones',
            'cargado_por', 'fecha_carga', 'fecha_actualizacion',
        ]
        read_only_fields = ['cargado_por', 'fecha_carga', 'fecha_actualizacion']
