"""Serializers de gestión de incidencias."""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import ComentarioIncidencia, Incidencia


class ComentarioIncidenciaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = ComentarioIncidencia
        fields = ['id', 'incidencia', 'usuario', 'usuario_username', 'comentario', 'es_accion', 'fecha']
        read_only_fields = ['usuario', 'fecha']

    def validate_comentario(self, value):
        if not value.strip():
            raise serializers.ValidationError('El comentario no puede estar vacío.')
        return value.strip()


class ReasignarIncidenciaSerializer(serializers.Serializer):
    responsable = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(is_active=True)
    )


class EntradaComentarioSerializer(serializers.Serializer):
    comentario = serializers.CharField()
    es_accion = serializers.BooleanField(required=False, default=False)


class IncidenciaSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    unidad_nombre = serializers.CharField(source='unidad.nombre', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    comentarios = ComentarioIncidenciaSerializer(many=True, read_only=True)

    class Meta:
        model = Incidencia
        fields = [
            'id', 'numero', 'fecha_creacion', 'empleado', 'empleado_nombre',
            'unidad', 'unidad_nombre', 'categoria', 'categoria_display',
            'titulo', 'descripcion', 'prioridad', 'prioridad_display',
            'estado', 'estado_display', 'responsable', 'creado_por',
            'documentacion', 'fecha_estimada_resolucion', 'fecha_resolucion',
            'fecha_actualizacion', 'comentarios',
        ]
        read_only_fields = [
            'numero', 'fecha_creacion', 'creado_por', 'estado',
            'fecha_resolucion', 'fecha_actualizacion',
        ]

    def validate(self, attrs):
        inicio = attrs.get('fecha_estimada_resolucion')
        fecha_base = (
            self.instance.fecha_creacion.date()
            if self.instance and self.instance.fecha_creacion
            else timezone.localdate()
        )
        if inicio and inicio < fecha_base:
            raise serializers.ValidationError({
                'fecha_estimada_resolucion':
                    'La fecha estimada no puede ser anterior a la fecha de creación.'
            })
        return attrs
