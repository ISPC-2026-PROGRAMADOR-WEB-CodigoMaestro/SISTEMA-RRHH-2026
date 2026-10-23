"""Serializers de control de asistencia."""
from django.db.models import Q
from rest_framework import serializers

from .models import (
    AsignacionJornada,
    Feriado,
    Jornada,
    Marcacion,
    RegistroAsistencia,
    Turno,
)


class TurnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Turno
        fields = [
            'id', 'nombre', 'hora_inicio', 'hora_fin',
            'minutos_tolerancia', 'activo',
        ]

    def validate(self, attrs):
        inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        fin = attrs.get('hora_fin', getattr(self.instance, 'hora_fin', None))
        if inicio is not None and inicio == fin:
            raise serializers.ValidationError({
                'hora_fin': 'El inicio y el fin del turno no pueden coincidir.'
            })
        return attrs


class JornadaSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(
        source='empleado.nombre_completo', read_only=True, allow_null=True,
    )
    turno_nombre = serializers.CharField(source='turno.nombre', read_only=True, allow_null=True)

    class Meta:
        model = Jornada
        fields = [
            'id', 'empleado', 'empleado_nombre', 'turno', 'turno_nombre',
            'dia_semana', 'vigencia_desde', 'vigencia_hasta', 'activa',
            'nombre', 'hora_entrada', 'hora_salida', 'tolerancia_minutos',
            'dias_laborables', 'es_predeterminada',
        ]

    def validate(self, attrs):
        empleado = attrs.get('empleado', getattr(self.instance, 'empleado', None))
        dia = attrs.get('dia_semana', getattr(self.instance, 'dia_semana', None))
        inicio = attrs.get('vigencia_desde', getattr(self.instance, 'vigencia_desde', None))
        fin = attrs.get('vigencia_hasta', getattr(self.instance, 'vigencia_hasta', None))
        activa = attrs.get('activa', getattr(self.instance, 'activa', True))
        nombre = attrs.get('nombre', getattr(self.instance, 'nombre', ''))
        hora_entrada = attrs.get('hora_entrada', getattr(self.instance, 'hora_entrada', None))
        hora_salida = attrs.get('hora_salida', getattr(self.instance, 'hora_salida', None))
        turno = attrs.get('turno', getattr(self.instance, 'turno', None))
        dias_laborables = attrs.get(
            'dias_laborables',
            getattr(self.instance, 'dias_laborables', '0,1,2,3,4'),
        )
        if fin and inicio and fin < inicio:
            raise serializers.ValidationError({
                'vigencia_hasta': 'La vigencia no puede finalizar antes de comenzar.'
            })

        if empleado:
            if not turno or dia is None or inicio is None:
                raise serializers.ValidationError(
                    'Las jornadas semanales requieren turno, día y fecha de inicio.'
                )
            jornadas = Jornada.objects.filter(
                empleado=empleado, dia_semana=dia, activa=True,
            )
            if self.instance:
                jornadas = jornadas.exclude(pk=self.instance.pk)
            overlap = jornadas.filter(
                Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=inicio)
            )
            if fin:
                overlap = overlap.filter(vigencia_desde__lte=fin)
            if activa and overlap.exists():
                raise serializers.ValidationError(
                    'El empleado ya tiene un turno vigente ese día de la semana.'
                )
        elif not nombre or hora_entrada is None or hora_salida is None:
            raise serializers.ValidationError(
                'Una jornada reutilizable requiere nombre, hora de entrada y hora de salida.'
            )
        if empleado and attrs.get('es_predeterminada', False):
            raise serializers.ValidationError({
                'es_predeterminada': 'Una jornada asignada a un empleado no puede ser predeterminada.'
            })
        if hora_entrada is not None and hora_entrada == hora_salida:
            raise serializers.ValidationError({
                'hora_salida': 'La hora de entrada y salida no pueden coincidir.'
            })
        try:
            dias = [int(dia) for dia in dias_laborables.split(',') if dia != '']
        except ValueError as exc:
            raise serializers.ValidationError({
                'dias_laborables': 'Usa días de semana separados por coma (0 a 6).'
            }) from exc
        if any(dia not in range(7) for dia in dias) or len(dias) != len(set(dias)):
            raise serializers.ValidationError({
                'dias_laborables': 'Los días deben ser únicos y estar entre 0 y 6.'
            })
        return attrs


class AsignacionJornadaSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    jornada_nombre = serializers.CharField(source='jornada.nombre', read_only=True)

    class Meta:
        model = AsignacionJornada
        fields = ['id', 'empleado', 'empleado_nombre', 'jornada', 'jornada_nombre']

    def validate_jornada(self, jornada):
        if jornada.empleado_id is not None or not jornada.activa:
            raise serializers.ValidationError(
                'Selecciona una jornada reutilizable activa, no una jornada semanal.'
            )
        return jornada


class FeriadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feriado
        fields = ['id', 'fecha', 'nombre', 'descripcion']


class RegistroAsistenciaSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    horario_esperado = serializers.SerializerMethodField()

    def get_horario_esperado(self, registro):
        from .services import obtener_horario_esperado

        esperado = obtener_horario_esperado(registro.empleado, registro.fecha)
        if esperado is None:
            return None
        return {
            'inicio': esperado.inicio,
            'fin': esperado.fin,
            'es_franco': esperado.es_franco,
            'fuente': esperado.fuente,
        }

    class Meta:
        model = RegistroAsistencia
        fields = [
            'id', 'empleado', 'empleado_nombre', 'fecha', 'hora_ingreso',
            'hora_egreso', 'horario_diario', 'horario_esperado', 'estado',
            'estado_display', 'tipo', 'tipo_display', 'minutos_tardanza',
            'minutos_extra', 'justificado', 'justificacion', 'observaciones',
            'cargado_por', 'fecha_carga', 'fecha_actualizacion',
        ]
        read_only_fields = [
            'horario_diario',
            'horario_esperado',
            'estado',
            'minutos_tardanza',
            'minutos_extra',
            'cargado_por',
            'fecha_carga',
            'fecha_actualizacion',
        ]


class MarcacionSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Marcacion
        fields = [
            'id', 'empleado', 'empleado_nombre', 'fecha_hora', 'tipo',
            'tipo_display', 'origen', 'ip', 'cargado_por', 'creado',
        ]
        read_only_fields = ['origen', 'ip', 'cargado_por', 'creado']


class ImportarMarcacionesSerializer(serializers.Serializer):
    archivo = serializers.FileField()


class CerrarDiaSerializer(serializers.Serializer):
    fecha = serializers.DateField(required=False)
