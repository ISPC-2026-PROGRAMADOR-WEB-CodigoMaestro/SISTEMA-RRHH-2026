"""Serializers de evaluación de desempeño."""
from django.db import transaction
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

    def validate(self, attrs):
        inicio = attrs.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fin = attrs.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError({'fecha_fin': 'El período no puede finalizar antes de comenzar.'})
        return attrs


class CriterioEvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterioEvaluacion
        fields = ['id', 'nombre', 'descripcion', 'peso', 'activo', 'orden']

    def validate_peso(self, value):
        if value <= 0:
            raise serializers.ValidationError('El peso debe ser mayor que cero.')
        return value


class DetalleEvaluacionSerializer(serializers.ModelSerializer):
    criterio_nombre = serializers.CharField(source='criterio.nombre', read_only=True)

    class Meta:
        model = DetalleEvaluacion
        fields = ['id', 'criterio', 'criterio_nombre', 'calificacion', 'observacion']

    def validate_calificacion(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('La calificación debe estar entre 0 y 100.')
        return value


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
        read_only_fields = [
            'estado', 'evaluador', 'calificacion_general',
            'fecha_creacion', 'fecha_actualizacion',
        ]

    def validate(self, attrs):
        periodo = attrs.get('periodo', getattr(self.instance, 'periodo', None))
        fecha = attrs.get('fecha_evaluacion', getattr(self.instance, 'fecha_evaluacion', None))
        if periodo and fecha and not periodo.fecha_inicio <= fecha <= periodo.fecha_fin:
            raise serializers.ValidationError({
                'fecha_evaluacion': 'La fecha de evaluación debe estar dentro del período seleccionado.'
            })
        if self.instance and self.instance.estado in (
            EvaluacionDesempeno.Estado.FINALIZADA,
            EvaluacionDesempeno.Estado.ANULADA,
        ):
            raise serializers.ValidationError(
                'No se puede modificar una evaluación finalizada o anulada.'
            )
        detalles = attrs.get('detalles')
        if detalles is not None:
            criterios = [detalle['criterio'].pk for detalle in detalles]
            if len(criterios) != len(set(criterios)):
                raise serializers.ValidationError({
                    'detalles': 'No repitas criterios dentro de la misma evaluación.'
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from .services import calcular_puntaje_ponderado

        detalles = validated_data.pop('detalles', [])
        puntaje = calcular_puntaje_ponderado(detalles)
        evaluacion = EvaluacionDesempeno.objects.create(
            **validated_data,
            calificacion_general=puntaje,
        )
        for detalle in detalles:
            DetalleEvaluacion.objects.create(evaluacion=evaluacion, **detalle)
        return evaluacion

    @transaction.atomic
    def update(self, instance, validated_data):
        from .services import calcular_puntaje_ponderado

        detalles = validated_data.pop('detalles', None)
        if detalles is not None:
            puntaje = calcular_puntaje_ponderado(detalles)
            instance.calificacion_general = puntaje
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save(update_fields=[
            *validated_data.keys(),
            *(['calificacion_general'] if detalles is not None else []),
            'fecha_actualizacion',
        ])
        if detalles is not None:
            instance.detalles.all().delete()
            for detalle in detalles:
                DetalleEvaluacion.objects.create(evaluacion=instance, **detalle)
        return instance
