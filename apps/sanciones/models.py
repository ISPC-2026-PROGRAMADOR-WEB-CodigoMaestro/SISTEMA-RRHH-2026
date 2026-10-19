"""Sanciones y antecedentes disciplinarios."""
from django.conf import settings
from django.db import models


class Sancion(models.Model):
    class Tipo(models.TextChoices):
        APERCIBIMIENTO = 'APERCIBIMIENTO', 'Apercibimiento'
        LLAMADO = 'LLAMADO', 'Llamado de atencion'
        SUSPENSION = 'SUSPENSION', 'Suspension'
        OTRA = 'OTRA', 'Otra medida'

    class Estado(models.TextChoices):
        EN_REVISION = 'EN_REVISION', 'En revision'
        NOTIFICADA = 'NOTIFICADA', 'Notificada'
        FIRME = 'FIRME', 'Firme'
        APELADA = 'APELADA', 'Apelada'
        FINALIZADA = 'FINALIZADA', 'Finalizada'

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='sanciones',
    )
    fecha_hecho = models.DateField('fecha del hecho')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    descripcion = models.TextField('descripcion de la situacion')
    normativa_incumplida = models.TextField('normativa o disposicion incumplida', blank=True)
    medida_adoptada = models.TextField()
    dias_suspension = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Solo aplica si el tipo es suspension',
    )
    descargo_trabajador = models.TextField(blank=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.EN_REVISION)
    documentacion = models.FileField(
        upload_to='sanciones/',
        null=True,
        blank=True,
        verbose_name='documentacion respaldatoria',
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sanciones_registradas',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'sancion'
        verbose_name_plural = 'sanciones'
        ordering = ['-fecha_hecho']

    def __str__(self):
        return f'{self.empleado.legajo} | {self.get_tipo_display()} | {self.fecha_hecho}'
