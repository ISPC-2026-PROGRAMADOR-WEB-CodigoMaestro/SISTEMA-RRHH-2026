"""
Modelos de estructura organizacional.
Areas, unidades funcionales y dependencias jerarquicas.
"""
from django.db import models


class UnidadOrganizacional(models.Model):
    """
    Nodo de la estructura organizacional (gerencia, area, departamento, sector, etc.).
    Soporta jerarquia via parent (organigrama).
    """

    class Tipo(models.TextChoices):
        DIRECCION = 'DIRECCION', 'Direccion'
        GERENCIA = 'GERENCIA', 'Gerencia'
        AREA = 'AREA', 'Area'
        DEPARTAMENTO = 'DEPARTAMENTO', 'Departamento'
        SECTOR = 'SECTOR', 'Sector'
        UNIDAD = 'UNIDAD', 'Unidad funcional'
        OTRO = 'OTRO', 'Otro'

    codigo = models.CharField('codigo', max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.AREA)
    descripcion = models.TextField('descripcion', blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='hijos',
        verbose_name='unidad padre',
    )
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0, help_text='Orden de visualizacion en organigrama')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'unidad organizacional'
        verbose_name_plural = 'unidades organizacionales'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'

    @property
    def ruta_jerarquica(self):
        nodos = []
        actual = self
        while actual is not None:
            nodos.append(actual.nombre)
            actual = actual.parent
        return ' / '.join(reversed(nodos))
