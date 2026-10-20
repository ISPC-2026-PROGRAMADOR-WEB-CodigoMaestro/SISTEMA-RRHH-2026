"""Serializers de vacaciones y licencias."""
from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import SaldoVacaciones, SolicitudLicencia, TipoLicencia
from .services import validar_solicitud


class TipoLicenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoLicencia
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'dias_maximos',
            'requiere_aprobacion', 'descuenta_vacaciones', 'activo',
        ]


class SaldoVacacionesSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    dias_pendientes = serializers.DecimalField(
        max_digits=5, decimal_places=1, read_only=True,
    )

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
            'dias_solicitados', 'estado', 'solicitado_por', 'revisado_por', 'fecha_revision',
            'fecha_solicitud', 'fecha_actualizacion',
        ]

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.estado not in (
            SolicitudLicencia.Estado.PENDIENTE,
            SolicitudLicencia.Estado.BORRADOR,
        ):
            raise serializers.ValidationError(
                'Solo se pueden editar solicitudes pendientes o en borrador.'
            )

        empleado = attrs.get('empleado', getattr(instance, 'empleado', None))
        tipo = attrs.get('tipo_licencia', getattr(instance, 'tipo_licencia', None))
        inicio = attrs.get('fecha_inicio', getattr(instance, 'fecha_inicio', None))
        fin = attrs.get('fecha_fin', getattr(instance, 'fecha_fin', None))
        try:
            dias = validar_solicitud(
                empleado,
                tipo,
                inicio,
                fin,
                excluir_id=instance.pk if instance else None,
            )
        except ValidationError as exc:
            detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            raise serializers.ValidationError(detail) from exc
        attrs['dias_solicitados'] = dias
        return attrs
