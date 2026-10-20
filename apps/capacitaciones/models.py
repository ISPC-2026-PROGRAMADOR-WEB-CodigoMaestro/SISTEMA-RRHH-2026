"""Cursos internos, inscripciones, asistencia y certificados."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Curso(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    instructor = models.CharField(max_length=150, blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    horas = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sesiones = models.PositiveSmallIntegerField(default=1)
    asistencia_minima = models.DecimalField(
        max_digits=5, decimal_places=2, default=80,
        help_text='Porcentaje mínimo de sesiones asistidas para certificar.',
    )
    cupo = models.PositiveIntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_inicio', 'nombre']

    def clean(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'El curso no puede finalizar antes de comenzar.'})
        if not 0 <= self.asistencia_minima <= 100:
            raise ValidationError({'asistencia_minima': 'El porcentaje debe estar entre 0 y 100.'})
        if self.horas <= 0:
            raise ValidationError({'horas': 'La duración debe ser mayor que cero.'})
        if self.sesiones < 1:
            raise ValidationError({'sesiones': 'El curso debe tener al menos una sesión.'})

    def __str__(self):
        return self.nombre


class Inscripcion(models.Model):
    class Estado(models.TextChoices):
        INSCRIPTO = 'INSCRIPTO', 'Inscripto'
        COMPLETADO = 'COMPLETADO', 'Completado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name='inscripciones')
    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.PROTECT,
        related_name='inscripciones_capacitacion',
    )
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.INSCRIPTO)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_inscripcion']
        constraints = [
            models.UniqueConstraint(fields=['curso', 'empleado'], name='capacitacion_curso_empleado_uniq'),
        ]

    def clean(self):
        if self.curso_id and self.empleado_id and self.estado != self.Estado.CANCELADO:
            inscriptos = Inscripcion.objects.filter(
                curso_id=self.curso_id,
            ).exclude(estado=self.Estado.CANCELADO)
            if self.pk:
                inscriptos = inscriptos.exclude(pk=self.pk)
            if self.curso.cupo is not None and inscriptos.count() >= self.curso.cupo:
                raise ValidationError({'curso': 'El curso ya alcanzó su cupo máximo.'})

    def __str__(self):
        return f'{self.empleado} - {self.curso}'


class AsistenciaCapacitacion(models.Model):
    inscripcion = models.ForeignKey(
        Inscripcion,
        on_delete=models.CASCADE,
        related_name='asistencias',
    )
    fecha = models.DateField()
    presente = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_capacitacion_registradas',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha']
        constraints = [
            models.UniqueConstraint(
                fields=['inscripcion', 'fecha'],
                name='capacitacion_asistencia_inscripcion_fecha_uniq',
            ),
        ]

    def clean(self):
        if self.inscripcion_id and not (
            self.inscripcion.curso.fecha_inicio <= self.fecha <= self.inscripcion.curso.fecha_fin
        ):
            raise ValidationError({'fecha': 'La asistencia debe corresponder a una fecha del curso.'})
        if self.inscripcion_id and self.inscripcion.estado == Inscripcion.Estado.CANCELADO:
            raise ValidationError({'inscripcion': 'No se puede registrar asistencia a una inscripción cancelada.'})
        if self.inscripcion_id:
            asistencias = AsistenciaCapacitacion.objects.filter(inscripcion_id=self.inscripcion_id)
            if self.pk:
                asistencias = asistencias.exclude(pk=self.pk)
            if asistencias.count() >= self.inscripcion.curso.sesiones:
                raise ValidationError({'inscripcion': 'Ya se registró la asistencia de todas las sesiones.'})

    def __str__(self):
        return f'{self.inscripcion} - {self.fecha}'


class Certificado(models.Model):
    inscripcion = models.OneToOneField(
        Inscripcion,
        on_delete=models.PROTECT,
        related_name='certificado',
    )
    documento_legajo = models.OneToOneField(
        'empleados.DocumentoLegajo',
        on_delete=models.PROTECT,
        related_name='certificado_capacitacion',
    )
    fecha_emision = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_emision']

    def __str__(self):
        return f'Certificado - {self.inscripcion.empleado} - {self.inscripcion.curso}'
