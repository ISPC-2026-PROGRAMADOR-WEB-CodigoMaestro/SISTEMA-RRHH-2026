"""Serializers de capacitación."""
from decimal import Decimal

from rest_framework import serializers

from .models import AsistenciaCapacitacion, Certificado, Curso, Inscripcion


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = [
            'id', 'nombre', 'descripcion', 'instructor', 'fecha_inicio',
            'fecha_fin', 'horas', 'sesiones', 'asistencia_minima', 'cupo',
            'activo',
        ]

    def validate(self, attrs):
        inicio = attrs.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fin = attrs.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))
        minimo = attrs.get('asistencia_minima', getattr(self.instance, 'asistencia_minima', Decimal('80')))
        horas = attrs.get('horas', getattr(self.instance, 'horas', Decimal('0')))
        sesiones = attrs.get('sesiones', getattr(self.instance, 'sesiones', 1))
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError({'fecha_fin': 'El curso no puede finalizar antes de comenzar.'})
        if not 0 <= minimo <= 100:
            raise serializers.ValidationError({'asistencia_minima': 'El porcentaje debe estar entre 0 y 100.'})
        if horas <= 0:
            raise serializers.ValidationError({'horas': 'La duración debe ser mayor que cero.'})
        if sesiones < 1:
            raise serializers.ValidationError({'sesiones': 'El curso debe tener al menos una sesión.'})
        return attrs


class InscripcionSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    estado = serializers.CharField(read_only=True)

    class Meta:
        model = Inscripcion
        fields = [
            'id', 'curso', 'curso_nombre', 'empleado', 'empleado_nombre',
            'estado', 'fecha_inscripcion', 'observaciones',
        ]
        read_only_fields = ['estado', 'fecha_inscripcion']

    def validate(self, attrs):
        curso = attrs.get('curso', getattr(self.instance, 'curso', None))
        empleado = attrs.get('empleado', getattr(self.instance, 'empleado', None))
        if curso and not curso.activo:
            raise serializers.ValidationError({'curso': 'El curso no está activo.'})
        if curso and empleado:
            query = Inscripcion.objects.filter(curso=curso, empleado=empleado)
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise serializers.ValidationError('El empleado ya está inscripto en este curso.')
            if curso.cupo is not None and Inscripcion.objects.filter(
                curso=curso,
            ).exclude(estado=Inscripcion.Estado.CANCELADO).count() >= curso.cupo:
                raise serializers.ValidationError({'curso': 'El curso ya alcanzó su cupo máximo.'})
        return attrs


class AsistenciaCapacitacionSerializer(serializers.ModelSerializer):
    registrada_por = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AsistenciaCapacitacion
        fields = [
            'id', 'inscripcion', 'fecha', 'presente', 'observaciones',
            'registrada_por', 'fecha_registro',
        ]
        read_only_fields = ['fecha_registro']

    def validate(self, attrs):
        inscripcion = attrs.get('inscripcion', getattr(self.instance, 'inscripcion', None))
        fecha = attrs.get('fecha', getattr(self.instance, 'fecha', None))
        if inscripcion and fecha and not (
            inscripcion.curso.fecha_inicio <= fecha <= inscripcion.curso.fecha_fin
        ):
            raise serializers.ValidationError({'fecha': 'La fecha debe estar dentro del curso.'})
        if inscripcion and inscripcion.estado == Inscripcion.Estado.CANCELADO:
            raise serializers.ValidationError({'inscripcion': 'La inscripción está cancelada.'})
        if inscripcion and fecha:
            asistencias = AsistenciaCapacitacion.objects.filter(inscripcion=inscripcion)
            if self.instance:
                asistencias = asistencias.exclude(pk=self.instance.pk)
            if asistencias.count() >= inscripcion.curso.sesiones:
                raise serializers.ValidationError(
                    {'inscripcion': 'Ya se registró la asistencia de todas las sesiones del curso.'}
                )
        return attrs


class CertificadoSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='inscripcion.empleado.nombre_completo', read_only=True)
    curso_nombre = serializers.CharField(source='inscripcion.curso.nombre', read_only=True)
    archivo = serializers.FileField(source='documento_legajo.archivo', read_only=True)

    class Meta:
        model = Certificado
        fields = [
            'id', 'inscripcion', 'empleado_nombre', 'curso_nombre',
            'documento_legajo', 'archivo', 'fecha_emision',
        ]
        read_only_fields = fields
