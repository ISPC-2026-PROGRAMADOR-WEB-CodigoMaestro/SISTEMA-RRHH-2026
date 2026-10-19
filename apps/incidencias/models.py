"""Gestion de incidencias de Recursos Humanos."""
from django.conf import settings
from django.db import models


class Incidencia(models.Model):
    class Categoria(models.TextChoices):
        ASISTENCIA = 'ASISTENCIA', 'Problema de asistencia'
        CONFLICTO = 'CONFLICTO', 'Conflicto laboral'
        LIQUIDACION = 'LIQUIDACION', 'Error de liquidacion'
        DOCUMENTACION = 'DOCUMENTACION', 'Falta de documentacion'
        ACCIDENTE = 'ACCIDENTE', 'Accidente'
        RECLAMO = 'RECLAMO', 'Reclamo'
        INCUMPLIMIENTO = 'INCUMPLIMIENTO', 'Incumplimiento'
        SOLICITUD = 'SOLICITUD', 'Solicitud especial'
        ADMINISTRATIVO = 'ADMINISTRATIVO', 'Inconveniente administrativo'
        OTRO = 'OTRO', 'Otro'

    class Prioridad(models.TextChoices):
        BAJA = 'BAJA', 'Baja'
        MEDIA = 'MEDIA', 'Media'
        ALTA = 'ALTA', 'Alta'
        CRITICA = 'CRITICA', 'Critica'

    class Estado(models.TextChoices):
        ABIERTA = 'ABIERTA', 'Abierta'
        ASIGNADA = 'ASIGNADA', 'Asignada'
        EN_ANALISIS = 'EN_ANALISIS', 'En analisis'
        PENDIENTE_DOC = 'PENDIENTE_DOC', 'Pendiente de documentacion'
        RESUELTA = 'RESUELTA', 'Resuelta'
        CERRADA = 'CERRADA', 'Cerrada'

    numero = models.CharField(max_length=20, unique=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidencias',
        help_text='Trabajador involucrado (opcional)',
    )
    unidad = models.ForeignKey(
        'organizacion.UnidadOrganizacional',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidencias',
        help_text='Area involucrada (opcional)',
    )
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidencias_asignadas',
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidencias_creadas',
    )
    documentacion = models.FileField(upload_to='incidencias/', null=True, blank=True)
    fecha_estimada_resolucion = models.DateField(null=True, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'incidencia'
        verbose_name_plural = 'incidencias'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.numero} - {self.titulo}'

    def save(self, *args, **kwargs):
        if not self.numero:
            from django.utils import timezone
            anio = timezone.localdate().year
            ultimo = (
                Incidencia.objects.filter(numero__startswith=f'INC-{anio}-')
                .order_by('-numero')
                .first()
            )
            seq = 1
            if ultimo:
                try:
                    seq = int(ultimo.numero.split('-')[-1]) + 1
                except ValueError:
                    seq = 1
            self.numero = f'INC-{anio}-{seq:05d}'
        super().save(*args, **kwargs)


class ComentarioIncidencia(models.Model):
    incidencia = models.ForeignKey(
        Incidencia,
        on_delete=models.CASCADE,
        related_name='comentarios',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    comentario = models.TextField()
    es_accion = models.BooleanField(
        default=False,
        help_text='Marca si registra una accion realizada',
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'comentario de incidencia'
        verbose_name_plural = 'comentarios de incidencia'
        ordering = ['fecha']

    def __str__(self):
        return f'{self.incidencia.numero} @ {self.fecha}'
