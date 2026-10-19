"""Serializers de evaluación de desempeño."""
from rest_framework import serializers

from .models import (
    CriterioEvaluacion,
    DetalleEvaluacion,
    EvaluacionDesempeno,
    PeriodoEvaluacion,
)


class PeriodoEvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoEvaluacion
        fields = ['id', 'nombre', 'fecha_inicio', 'fecha_fin', 'activo', 'descripcion']


class CriterioEvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterioEvaluacion
        fields = ['id', 'nombre', 'descripcion', 'peso', 'activo', 'orden']


class DetalleEvaluacionSerializer(serializers.ModelSerializer):
    criterio_nombre = serializers.CharField(source='criterio.nombre', read_only=True)

    class Meta:
        model = DetalleEvaluacion
        fields = ['id', 'criterio', 'criterio_nombre', 'calificacion', 'observacion']


class EvaluacionDesempenoSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    periodo_nombre = serializers.CharField(source='periodo.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    detalles = DetalleEvaluacionSerializer(many=True, required=False)

    class Meta:
        model = EvaluacionDesempeno
        fields = [
            'id', 'empleado', 'empleado_nombre', 'periodo', 'periodo_nombre',
            'evaluador', 'fecha_evaluacion', 'estado', 'estado_display',
            'calificacion_general', 'fortalezas', 'aspectos_mejorar',
            'objetivos_futuros', 'plan_desarrollo', 'observaciones',
            'detalles', 'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']

    def create(self, validated_data):
        detalles = validated_data.pop('detalles', [])
        evaluacion = EvaluacionDesempeno.objects.create(**validated_data)
        for detalle in detalles:
            DetalleEvaluacion.objects.create(evaluacion=evaluacion, **detalle)
        return evaluacion

    def update(self, instance, validated_data):
        detalles = validated_data.pop('detalles', None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if detalles is not None:
            instance.detalles.all().delete()
            for detalle in detalles:
                DetalleEvaluacion.objects.create(evaluacion=instance, **detalle)
        return instance
