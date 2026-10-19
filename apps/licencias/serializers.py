"""Serializers de vacaciones y licencias."""
from rest_framework import serializers

from .models import SaldoVacaciones, SolicitudLicencia, TipoLicencia


class TipoLicenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoLicencia
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'dias_maximos',
            'requiere_aprobacion', 'descuenta_vacaciones', 'activo',
        ]


class SaldoVacacionesSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)

    class Meta:
        model = SaldoVacaciones
        fields = [
            'id', 'empleado', 'empleado_nombre', 'anio',
            'dias_correspondientes', 'dias_usados', 'dias_pendientes',
            'observaciones',
        ]


class SolicitudLicenciaSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    tipo_nombre = serializers.CharField(source='tipo_licencia.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = SolicitudLicencia
        fields = [
            'id', 'empleado', 'empleado_nombre', 'tipo_licencia', 'tipo_nombre',
            'fecha_inicio', 'fecha_fin', 'dias_solicitados', 'motivo',
            'estado', 'estado_display', 'solicitado_por', 'revisado_por',
            'fecha_revision', 'observacion_revision',
            'fecha_solicitud', 'fecha_actualizacion',
        ]
        read_only_fields = [
            'solicitado_por', 'revisado_por', 'fecha_revision',
            'fecha_solicitud', 'fecha_actualizacion',
        ]
