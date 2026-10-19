"""
Modelos de puestos, cargos y designaciones (planta funcional).
"""
from django.db import models


class Puesto(models.Model):
    """Ficha de puesto de trabajo: denominacion, ubicacion, funciones, requisitos."""

    class NivelAutoridad(models.TextChoices):
        OPERATIVO = 'OPERATIVO', 'Operativo'
        SUPERVISION = 'SUPERVISION', 'Supervision'
        JEFATURA = 'JEFATURA', 'Jefatura'
        GERENCIA = 'GERENCIA', 'Gerencia'
        DIRECCION = 'DIRECCION', 'Direccion'

    codigo = models.CharField('codigo', max_length=30, unique=True)
    denominacion = models.CharField('denominacion', max_length=150)
    unidad = models.ForeignKey(
        'organizacion.UnidadOrganizacional',
        on_delete=models.PROTECT,
        related_name='puestos',
        verbose_name='unidad organizacional',
    )
    puesto_superior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='puestos_a_cargo',
        verbose_name='dependencia jerarquica',
    )
    objetivo_general = models.TextField(blank=True)
    funciones_principales = models.TextField(blank=True)
    tareas = models.TextField(blank=True)
    responsabilidades = models.TextField(blank=True)
    nivel_autoridad = models.CharField(
        max_length=20,
        choices=NivelAutoridad.choices,
        default=NivelAutoridad.OPERATIVO,
    )
    formacion_requerida = models.TextField('formacion requerida', blank=True)
    experiencia_requerida = models.TextField('experiencia requerida', blank=True)
    conocimientos = models.TextField(blank=True)
    competencias = models.TextField(blank=True)
    habilidades = models.TextField(blank=True)
    condiciones_trabajo = models.TextField('condiciones de trabajo', blank=True)
    cantidad_prevista = models.PositiveIntegerField(
        'cargos previstos',
        default=1,
        help_text='Cantidad de posiciones previstas para este puesto',
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'puesto'
        verbose_name_plural = 'puestos'
        ordering = ['denominacion']

    def __str__(self):
        return f'{self.codigo} - {self.denominacion}'

    @property
    def cantidad_ocupados(self):
        return self.designaciones.filter(activa=True).count()

    @property
    def cantidad_vacantes(self):
        return max(0, self.cantidad_prevista - self.cantidad_ocupados)


class Designacion(models.Model):
    """Asignacion de un empleado a un puesto (planta funcional)."""

    class ModalidadContractual(models.TextChoices):
        RELACION_DEPENDENCIA = 'RD', 'Relacion de dependencia'
        CONTRATO_PLAZO = 'CP', 'Contrato a plazo fijo'
        PASANTIA = 'PA', 'Pasantia'
        MONOTRIBUTO = 'MO', 'Monotributo / locacion'
        OTRO = 'OT', 'Otro'

    class Jornada(models.TextChoices):
        COMPLETA = 'COMPLETA', 'Jornada completa'
        PARCIAL = 'PARCIAL', 'Jornada parcial'
        REDUCIDA = 'REDUCIDA', 'Jornada reducida'
        POR_TURNOS = 'TURNOS', 'Por turnos'

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.PROTECT,
        related_name='designaciones',
    )
    puesto = models.ForeignKey(
        Puesto,
        on_delete=models.PROTECT,
        related_name='designaciones',
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    funciones_desempenadas = models.TextField('funciones desempenadas', blank=True)
    modalidad_contractual = models.CharField(
        max_length=5,
        choices=ModalidadContractual.choices,
        default=ModalidadContractual.RELACION_DEPENDENCIA,
    )
    jornada = models.CharField(
        max_length=15,
        choices=Jornada.choices,
        default=Jornada.COMPLETA,
    )
    superior_jerarquico = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinados_designacion',
        verbose_name='superior jerarquico',
    )
    activa = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'designacion'
        verbose_name_plural = 'designaciones'
        ordering = ['-fecha_inicio']

    def __str__(self):
        estado = 'activa' if self.activa else 'finalizada'
        return f'{self.empleado} -> {self.puesto} ({estado})'
