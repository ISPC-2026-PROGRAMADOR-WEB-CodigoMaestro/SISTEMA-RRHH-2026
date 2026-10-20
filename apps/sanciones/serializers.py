"""Serializers de sanciones disciplinarias."""
from django.utils import timezone
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
        read_only_fields = [
            'estado', 'fecha_registro', 'fecha_actualizacion', 'responsable',
            'fecha_notificacion', 'fecha_aplicacion', 'fecha_apelacion',
        ]

    def validate(self, attrs):
        if self.instance and self.instance.estado != Sancion.Estado.PROPUESTA:
            raise serializers.ValidationError(
                'Solo se pueden editar sanciones en estado de propuesta.'
            )
        tipo = attrs.get('tipo', getattr(self.instance, 'tipo', None))
        dias = attrs.get('dias_suspension', getattr(self.instance, 'dias_suspension', None))
        fecha_hecho = attrs.get('fecha_hecho', getattr(self.instance, 'fecha_hecho', None))
        if tipo == Sancion.Tipo.SUSPENSION and not dias:
            raise serializers.ValidationError({
                'dias_suspension': 'Una suspensión debe indicar la cantidad de días.'
            })
        if tipo != Sancion.Tipo.SUSPENSION and dias:
            raise serializers.ValidationError({
                'dias_suspension': 'Solo las suspensiones admiten días de suspensión.'
            })
        if fecha_hecho and fecha_hecho > timezone.localdate():
            raise serializers.ValidationError({
                'fecha_hecho': 'La fecha del hecho no puede ser futura.'
            })
        return attrs
