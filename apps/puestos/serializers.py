"""Serializers de puestos, cargos y designaciones."""
from rest_framework import serializers

from .models import Designacion, Puesto


class DesignacionSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    puesto_denominacion = serializers.CharField(source='puesto.denominacion', read_only=True)

    class Meta:
        model = Designacion
        fields = [
            'id', 'empleado', 'empleado_nombre', 'puesto', 'puesto_denominacion',
            'fecha_inicio', 'fecha_fin', 'funciones_desempenadas',
            'modalidad_contractual', 'jornada', 'superior_jerarquico', 'activa',
            'observaciones', 'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class PuestoSerializer(serializers.ModelSerializer):
    unidad_nombre = serializers.CharField(source='unidad.nombre', read_only=True)
    cantidad_ocupados = serializers.IntegerField(read_only=True)
    cantidad_vacantes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Puesto
        fields = [
            'id', 'codigo', 'denominacion', 'unidad', 'unidad_nombre',
            'puesto_superior', 'objetivo_general', 'funciones_principales',
            'tareas', 'responsabilidades', 'nivel_autoridad',
            'formacion_requerida', 'experiencia_requerida', 'conocimientos',
            'competencias', 'habilidades', 'condiciones_trabajo',
            'cantidad_prevista', 'cantidad_ocupados', 'cantidad_vacantes',
            'activo', 'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']
