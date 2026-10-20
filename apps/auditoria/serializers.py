"""Serializers de la bitácora de auditoría."""
from rest_framework import serializers

from .models import RegistroAuditoria


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)

    class Meta:
        model = RegistroAuditoria
        fields = [
            'id', 'usuario', 'usuario_username', 'fecha_hora', 'accion',
            'accion_display', 'modelo', 'objeto_id', 'descripcion',
            'datos_anteriores', 'datos_nuevos', 'ip', 'user_agent', 'ruta',
        ]
        read_only_fields = fields
