"""Control de asistencia del personal."""
from django.conf import settings
from django.db import models


class RegistroAsistencia(models.Model):
    class Tipo(models.TextChoices):
        PRESENTE = 'PRESENTE', 'Presente'
        AUSENTE = 'AUSENTE', 'Ausente'
        TARDANZA = 'TARDANZA', 'Tardanza'
        RETIRO_ANTICIPADO = 'RETIRO', 'Retiro anticipado'
        HORA_EXTRA = 'HEXTRA', 'Hora extra'
        FERIADO = 'FERIADO', 'Feriado / no laborable'
        HOME_OFFICE = 'HOME', 'Home office'

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='asistencias',
    )
    fecha = models.DateField()
    hora_ingreso = models.TimeField(null=True, blank=True)
    hora_egreso = models.TimeField(null=True, blank=True)
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.PRESENTE)
    minutos_tardanza = models.PositiveIntegerField(default=0)
    minutos_extra = models.PositiveIntegerField(default=0)
    justificado = models.BooleanField(default=False)
    justificacion = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_cargadas',
    )
    fecha_carga = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'registro de asistencia'
        verbose_name_plural = 'registros de asistencia'
        ordering = ['-fecha']
        unique_together = [('empleado', 'fecha')]

    def __str__(self):
        return f'{self.empleado.legajo} | {self.fecha} | {self.get_tipo_display()}'
