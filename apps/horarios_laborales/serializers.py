from rest_framework import serializers
from django.db import transaction

from .models import HorarioDiario, HorarioPredeterminado
from .services import establecer_horario_predeterminado


class HorarioDiarioSerializer(serializers.ModelSerializer):
    alcance = serializers.ChoiceField(
        choices=[
            ('solo_fecha', 'Solo esta fecha'),
            ('predeterminado', 'Cambiar el horario predeterminado desde esta fecha'),
        ],
        default='solo_fecha',
        write_only=True,
    )
    empleado_nombre = serializers.CharField(
        source='empleado.nombre_completo',
        read_only=True,
    )

    class Meta:
        model = HorarioDiario
        fields = [
            'id',
            'alcance',
            'empleado',
            'empleado_nombre',
            'fecha',
            'hora_entrada',
            'hora_salida',
            'es_franco',
            'observaciones',
            'creado_por',
            'creado_en',
            'modificado_en',
        ]
        read_only_fields = ['creado_por', 'creado_en', 'modificado_en']

    def validate(self, attrs):
        empleado = attrs.get('empleado', getattr(self.instance, 'empleado', None))
        fecha = attrs.get('fecha', getattr(self.instance, 'fecha', None))
        es_franco = attrs.get('es_franco', getattr(self.instance, 'es_franco', False))
        hora_entrada = attrs.get(
            'hora_entrada',
            getattr(self.instance, 'hora_entrada', None),
        )
        hora_salida = attrs.get(
            'hora_salida',
            getattr(self.instance, 'hora_salida', None),
        )
        alcance = attrs.get('alcance', 'solo_fecha')

        if es_franco:
            if hora_entrada is not None or hora_salida is not None:
                raise serializers.ValidationError(
                    'Un día franco no puede tener hora de entrada ni de salida.'
                )
            if alcance == 'predeterminado':
                raise serializers.ValidationError({
                    'alcance': 'Un día franco no puede ser horario predeterminado.'
                })
        elif hora_entrada is None or hora_salida is None:
            raise serializers.ValidationError({
                'hora_entrada': 'La entrada y la salida son obligatorias si no es franco.',
                'hora_salida': 'La entrada y la salida son obligatorias si no es franco.',
            })

        duplicados = HorarioDiario.objects.filter(empleado=empleado, fecha=fecha)
        if self.instance is not None:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if empleado is not None and fecha is not None and duplicados.exists():
            raise serializers.ValidationError(
                'Ya existe un horario diario para este empleado y fecha.'
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        alcance = validated_data.pop('alcance', 'solo_fecha')
        horario = super().create(validated_data)
        tiene_predeterminado = HorarioPredeterminado.objects.filter(
            empleado=horario.empleado,
        ).exists()
        if not horario.es_franco and (
            alcance == 'predeterminado' or not tiene_predeterminado
        ):
            establecer_horario_predeterminado(
                horario.empleado,
                horario.fecha,
                horario.hora_entrada,
                horario.hora_salida,
                horario.observaciones,
                self.context['request'].user,
            )
        return horario

    @transaction.atomic
    def update(self, instance, validated_data):
        alcance = validated_data.pop('alcance', 'solo_fecha')
        horario = super().update(instance, validated_data)
        if alcance == 'predeterminado' and not horario.es_franco:
            establecer_horario_predeterminado(
                horario.empleado,
                horario.fecha,
                horario.hora_entrada,
                horario.hora_salida,
                horario.observaciones,
                self.context['request'].user,
            )
        return horario
