"""
Modelos de empleados, legajo digital, documentacion e historial laboral.
"""
from django.conf import settings
from django.db import models


def legajo_upload_to(instance, filename):
    legajo = instance.empleado.legajo if instance.empleado_id else 'sin_legajo'
    return f'legajos/{legajo}/{filename}'


class Empleado(models.Model):
    """Trabajador de la empresa: datos personales, laborales, contractuales y de contacto."""

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        LICENCIA = 'LICENCIA', 'En licencia'
        SUSPENDIDO = 'SUSPENDIDO', 'Suspendido'
        BAJA = 'BAJA', 'Baja'

    class TipoDocumento(models.TextChoices):
        DNI = 'DNI', 'DNI'
        LC = 'LC', 'Libreta civica'
        LE = 'LE', 'Libreta de enrolamiento'
        PASAPORTE = 'PAS', 'Pasaporte'
        CUIL = 'CUIL', 'CUIL/CUIT'
        OTRO = 'OTRO', 'Otro'

    class Genero(models.TextChoices):
        FEMENINO = 'F', 'Femenino'
        MASCULINO = 'M', 'Masculino'
        X = 'X', 'No binario / otro'
        NC = 'NC', 'Prefiere no decir'

    # Identificacion
    legajo = models.CharField(max_length=20, unique=True)
    tipo_documento = models.CharField(max_length=5, choices=TipoDocumento.choices, default=TipoDocumento.DNI)
    numero_documento = models.CharField(max_length=20)
    cuil = models.CharField('CUIL', max_length=15, blank=True)

    # Datos personales
    apellido = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=2, choices=Genero.choices, blank=True)
    nacionalidad = models.CharField(max_length=60, blank=True)
    estado_civil = models.CharField(max_length=40, blank=True)

    # Contacto
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    telefono_alternativo = models.CharField(max_length=40, blank=True)
    domicilio = models.CharField(max_length=200, blank=True)
    localidad = models.CharField(max_length=100, blank=True)
    provincia = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=20, blank=True)

    # Laborales / contractuales
    fecha_ingreso = models.DateField()
    fecha_egreso = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.ACTIVO)
    unidad = models.ForeignKey(
        'organizacion.UnidadOrganizacional',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empleados',
        verbose_name='unidad organizacional',
    )
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empleado',
    )
    foto = models.ImageField(upload_to='fotos_empleados/', null=True, blank=True)
    observaciones = models.TextField(blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'empleado'
        verbose_name_plural = 'empleados'
        ordering = ['apellido', 'nombre']
        unique_together = [('tipo_documento', 'numero_documento')]

    def __str__(self):
        return f'{self.legajo} - {self.apellido}, {self.nombre}'

    @property
    def nombre_completo(self):
        return f'{self.apellido}, {self.nombre}'

    @property
    def designacion_activa(self):
        return self.designaciones.filter(activa=True).select_related('puesto').first()


class CategoriaDocumento(models.Model):
    """Clasificacion de documentos del legajo digital."""

    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    requiere_vencimiento = models.BooleanField(
        default=False,
        help_text='Si True, se alertara por vencimiento',
    )
    dias_alerta_previa = models.PositiveIntegerField(
        default=30,
        help_text='Dias antes del vencimiento para generar alerta',
    )
    sensible = models.BooleanField(
        default=False,
        help_text='Documento sensible: acceso restringido por rol',
    )
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'categoria de documento'
        verbose_name_plural = 'categorias de documento'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class DocumentoLegajo(models.Model):
    """Documento adjunto al legajo digital del trabajador."""

    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name='documentos',
    )
    categoria = models.ForeignKey(
        CategoriaDocumento,
        on_delete=models.PROTECT,
        related_name='documentos',
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    archivo = models.FileField(upload_to=legajo_upload_to)
    fecha_emision = models.DateField(null=True, blank=True)
    fecha_presentacion = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_cargados',
    )
    fecha_carga = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'documento de legajo'
        verbose_name_plural = 'documentos de legajo'
        ordering = ['-fecha_carga']

    def __str__(self):
        return f'{self.empleado.legajo} - {self.titulo}'

    @property
    def esta_vencido(self):
        from django.utils import timezone
        if not self.fecha_vencimiento:
            return False
        return self.fecha_vencimiento < timezone.localdate()


class HistorialLaboral(models.Model):
    """
    Historial cronologico de la vida laboral del trabajador.
    La informacion NO se elimina (trazabilidad).
    """

    class TipoMovimiento(models.TextChoices):
        ALTA = 'ALTA', 'Alta'
        BAJA = 'BAJA', 'Baja'
        CAMBIO_CARGO = 'CAMBIO_CARGO', 'Cambio de cargo'
        PROMOCION = 'PROMOCION', 'Promocion'
        TRASLADO = 'TRASLADO', 'Traslado'
        MOD_JORNADA = 'MOD_JORNADA', 'Modificacion de jornada'
        LICENCIA = 'LICENCIA', 'Licencia'
        VACACIONES = 'VACACIONES', 'Vacaciones'
        AUSENCIA = 'AUSENCIA', 'Ausencia'
        CAPACITACION = 'CAPACITACION', 'Capacitacion'
        EVALUACION = 'EVALUACION', 'Evaluacion'
        RECONOCIMIENTO = 'RECONOCIMIENTO', 'Reconocimiento'
        SANCION = 'SANCION', 'Sancion'
        ACCIDENTE = 'ACCIDENTE', 'Accidente laboral'
        CAMBIO_CONTRACTUAL = 'CAMBIO_CONTRACTUAL', 'Cambio contractual'
        OTRO = 'OTRO', 'Otro'

    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name='historial',
    )
    fecha = models.DateField()
    tipo_movimiento = models.CharField(max_length=30, choices=TipoMovimiento.choices)
    descripcion = models.TextField()
    observaciones = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_cargados',
    )
    referencia_app = models.CharField(
        max_length=50,
        blank=True,
        help_text='App de origen (ej: sanciones, licencias)',
    )
    referencia_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='ID del registro de origen',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'historial laboral'
        verbose_name_plural = 'historiales laborales'
        ordering = ['-fecha', '-fecha_registro']

    def __str__(self):
        return f'{self.empleado.legajo} | {self.fecha} | {self.get_tipo_movimiento_display()}'

    def delete(self, *args, **kwargs):
        raise models.ProtectedError(
            'El historial laboral no puede eliminarse (trazabilidad).',
            self,
        )
