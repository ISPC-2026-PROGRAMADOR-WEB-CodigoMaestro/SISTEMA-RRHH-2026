"""Evaluacion de desempeno."""
from django.conf import settings
from django.db import models


class PeriodoEvaluacion(models.Model):
    nombre = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'periodo de evaluacion'
        verbose_name_plural = 'periodos de evaluacion'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return self.nombre


class CriterioEvaluacion(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    peso = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1,
        help_text='Peso relativo del criterio',
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'criterio de evaluacion'
        verbose_name_plural = 'criterios de evaluacion'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class EvaluacionDesempeno(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', 'Borrador'
        EN_CURSO = 'EN_CURSO', 'En curso'
        FINALIZADA = 'FINALIZADA', 'Finalizada'
        ANULADA = 'ANULADA', 'Anulada'

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='evaluaciones',
    )
    periodo = models.ForeignKey(
        PeriodoEvaluacion,
        on_delete=models.PROTECT,
        related_name='evaluaciones',
    )
    evaluador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluaciones_realizadas',
    )
    fecha_evaluacion = models.DateField()
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.BORRADOR)
    calificacion_general = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    fortalezas = models.TextField(blank=True)
    aspectos_mejorar = models.TextField('aspectos a mejorar', blank=True)
    objetivos_futuros = models.TextField(blank=True)
    plan_desarrollo = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'evaluacion de desempeno'
        verbose_name_plural = 'evaluaciones de desempeno'
        ordering = ['-fecha_evaluacion']

    def __str__(self):
        return f'{self.empleado.legajo} | {self.periodo} | {self.fecha_evaluacion}'


class DetalleEvaluacion(models.Model):
    evaluacion = models.ForeignKey(
        EvaluacionDesempeno,
        on_delete=models.CASCADE,
        related_name='detalles',
    )
    criterio = models.ForeignKey(
        CriterioEvaluacion,
        on_delete=models.PROTECT,
        related_name='detalles',
    )
    calificacion = models.DecimalField(max_digits=5, decimal_places=2)
    observacion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'detalle de evaluacion'
        verbose_name_plural = 'detalles de evaluacion'
        unique_together = [('evaluacion', 'criterio')]

    def __str__(self):
        return f'{self.evaluacion_id} - {self.criterio}: {self.calificacion}'
