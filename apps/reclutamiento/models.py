
"""
Modelos de vacantes, postulantes y procesos de seleccion de personal.
"""
from django.db import models


class Vacante(models.Model):
    """Busqueda laboral asociada a un puesto de trabajo."""

    class Estado(models.TextChoices):
        ABIERTA = 'ABIERTA', 'Abierta'
        PAUSADA = 'PAUSADA', 'Pausada'
        CERRADA = 'CERRADA', 'Cerrada'

    puesto = models.ForeignKey(
        'puestos.Puesto',
        on_delete=models.PROTECT,
        related_name='vacantes_reclutamiento',
    )
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    requisitos = models.TextField(blank=True)
    cantidad_vacantes = models.PositiveIntegerField(default=1)
    fecha_publicacion = models.DateField()
    fecha_cierre = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ABIERTA,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'vacante'
        verbose_name_plural = 'vacantes'
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return f'{self.titulo} - {self.puesto.denominacion}'


class Postulante(models.Model):
    """Persona interesada en participar de un proceso de seleccion."""

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    numero_documento = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    telefono = models.CharField(max_length=40, blank=True)
    formacion = models.TextField(blank=True)
    experiencia = models.TextField(blank=True)
    curriculum = models.FileField(
        upload_to='curriculums/',
        null=True,
        blank=True,
    )
    observaciones = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'postulante'
        verbose_name_plural = 'postulantes'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.apellido}, {self.nombre}'


class Postulacion(models.Model):
    """Relacion entre un postulante y una vacante disponible."""

    class Estado(models.TextChoices):
        RECIBIDA = 'RECIBIDA', 'Recibida'
        EVALUACION = 'EVALUACION', 'En evaluacion'
        ENTREVISTA = 'ENTREVISTA', 'En entrevista'
        SELECCIONADA = 'SELECCIONADA', 'Seleccionada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    postulante = models.ForeignKey(
        Postulante,
        on_delete=models.PROTECT,
        related_name='postulaciones',
    )
    vacante = models.ForeignKey(
        Vacante,
        on_delete=models.PROTECT,
        related_name='postulaciones',
    )
    fecha_postulacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.RECIBIDA,
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'postulacion'
        verbose_name_plural = 'postulaciones'
        ordering = ['-fecha_postulacion']
        unique_together = [('postulante', 'vacante')]

    def __str__(self):
        return f'{self.postulante} - {self.vacante.titulo}'


class Entrevista(models.Model):
    """Entrevista realizada durante un proceso de seleccion."""

    class Resultado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        FAVORABLE = 'FAVORABLE', 'Favorable'
        DESFAVORABLE = 'DESFAVORABLE', 'Desfavorable'

    postulacion = models.ForeignKey(
        Postulacion,
        on_delete=models.PROTECT,
        related_name='entrevistas',
    )
    fecha = models.DateTimeField()
    entrevistador = models.CharField(max_length=150)
    observaciones = models.TextField(blank=True)
    resultado = models.CharField(
        max_length=20,
        choices=Resultado.choices,
        default=Resultado.PENDIENTE,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'entrevista'
        verbose_name_plural = 'entrevistas'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.postulacion.postulante} - {self.fecha}'
