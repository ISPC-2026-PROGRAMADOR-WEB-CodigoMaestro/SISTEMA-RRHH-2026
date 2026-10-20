"""Vacaciones y licencias."""
from django.conf import settings
from django.db import models


class TipoLicencia(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    dias_maximos = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Tope de dias por solicitud (opcional)',
    )
    requiere_aprobacion = models.BooleanField(default=True)
    descuenta_vacaciones = models.BooleanField(
        default=False,
        help_text='Si True, descuenta del saldo de vacaciones',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'tipo de licencia'
        verbose_name_plural = 'tipos de licencia'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class SaldoVacaciones(models.Model):
    """Dias de vacaciones disponibles / utilizados por empleado y periodo."""

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='saldos_vacaciones',
    )
    anio = models.PositiveIntegerField('anio')
    dias_correspondientes = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    dias_usados = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'saldo de vacaciones'
        verbose_name_plural = 'saldos de vacaciones'
        unique_together = [('empleado', 'anio')]
        ordering = ['-anio']

    def __str__(self):
        return f'{self.empleado.legajo} | {self.anio} | pend: {self.dias_pendientes}'

    @property
    def dias_pendientes(self):
        return self.dias_correspondientes - self.dias_usados


class SolicitudLicencia(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', 'Borrador'
        PENDIENTE = 'PENDIENTE', 'Pendiente de revision'
        APROBADA = 'APROBADA', 'Aprobada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'
        CANCELADA = 'CANCELADA', 'Cancelada'
        MODIFICADA = 'MODIFICADA', 'Modificada'

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='solicitudes_licencia',
    )
    tipo_licencia = models.ForeignKey(
        TipoLicencia,
        on_delete=models.PROTECT,
        related_name='solicitudes',
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    dias_solicitados = models.DecimalField(max_digits=5, decimal_places=1)
    dias_descontados = models.JSONField(
        default=dict,
        blank=True,
        help_text='Días descontados por año para poder revertir exactamente una cancelación.',
    )
    motivo = models.TextField(blank=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='licencias_solicitadas',
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='licencias_revisadas',
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)
    observacion_revision = models.TextField(blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'solicitud de licencia'
        verbose_name_plural = 'solicitudes de licencia'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'{self.empleado.legajo} | {self.tipo_licencia} | {self.fecha_inicio} - {self.fecha_fin}'
