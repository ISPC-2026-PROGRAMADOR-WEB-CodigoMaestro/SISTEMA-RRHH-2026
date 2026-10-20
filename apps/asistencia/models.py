"""Control de asistencia del personal."""
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class Turno(models.Model):
    """Horario base de trabajo, reutilizable por varias jornadas."""

    nombre = models.CharField(max_length=100, unique=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    minutos_tolerancia = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def clean(self):
        if self.hora_inicio == self.hora_fin:
            raise ValidationError({'hora_fin': 'El inicio y el fin del turno no pueden coincidir.'})

    def __str__(self):
        return f'{self.nombre} ({self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M})'


class Jornada(models.Model):
    """Jornada reutilizable o asignación semanal histórica de un empleado."""

    DIAS_SEMANA = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'),
        (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='jornadas',
        null=True,
        blank=True,
    )
    turno = models.ForeignKey(
        Turno,
        on_delete=models.PROTECT,
        related_name='jornadas',
        null=True,
        blank=True,
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DIAS_SEMANA, null=True, blank=True)
    vigencia_desde = models.DateField(null=True, blank=True)
    vigencia_hasta = models.DateField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    nombre = models.CharField(max_length=100, blank=True, default='')
    hora_entrada = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
    tolerancia_minutos = models.PositiveIntegerField(default=10)
    dias_laborables = models.CharField(max_length=13, default='0,1,2,3,4')
    es_predeterminada = models.BooleanField(default=False)

    class Meta:
        ordering = ['nombre', 'empleado__apellido', 'dia_semana', 'vigencia_desde']
        constraints = [
            models.UniqueConstraint(
                fields=['empleado', 'dia_semana', 'vigencia_desde'],
                name='asistencia_jornada_empleado_dia_desde_uniq',
            ),
            models.UniqueConstraint(
                fields=['es_predeterminada'],
                condition=models.Q(es_predeterminada=True),
                name='asistencia_una_jornada_predeterminada',
            ),
        ]

    def clean(self):
        if self.empleado_id:
            if not self.turno_id or self.dia_semana is None or self.vigencia_desde is None:
                raise ValidationError(
                    'Las jornadas semanales requieren empleado, turno, día y fecha de inicio.'
                )
            if self.es_predeterminada:
                raise ValidationError({'es_predeterminada': 'Una jornada semanal no puede ser predeterminada.'})
        elif not self.nombre or not self.hora_entrada or not self.hora_salida:
            raise ValidationError(
                'Una jornada reutilizable requiere nombre, hora de entrada y hora de salida.'
            )
        if self.hora_entrada is not None and self.hora_entrada == self.hora_salida:
            raise ValidationError({'hora_salida': 'La hora de entrada y salida no pueden coincidir.'})
        if self.vigencia_hasta and self.vigencia_desde and self.vigencia_hasta < self.vigencia_desde:
            raise ValidationError({'vigencia_hasta': 'La vigencia no puede finalizar antes de comenzar.'})
        try:
            dias = [int(dia) for dia in self.dias_laborables.split(',') if dia != '']
        except ValueError as exc:
            raise ValidationError({'dias_laborables': 'Usa días de semana separados por coma (0 a 6).'}) from exc
        if any(dia not in range(7) for dia in dias) or len(dias) != len(set(dias)):
            raise ValidationError({'dias_laborables': 'Los días deben ser únicos y estar entre 0 y 6.'})

    def __str__(self):
        if not self.empleado_id:
            return self.nombre
        return f'{self.empleado} - {self.get_dia_semana_display()} - {self.turno}'


class AsignacionJornada(models.Model):
    empleado = models.OneToOneField(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='asignacion_jornada',
    )
    jornada = models.ForeignKey(
        Jornada,
        on_delete=models.PROTECT,
        related_name='asignaciones',
    )

    def __str__(self):
        return f'{self.empleado} - {self.jornada}'


class Feriado(models.Model):
    fecha = models.DateField(unique=True)
    nombre = models.CharField(max_length=150, blank=True, default='')
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f'{self.fecha} - {self.nombre}'


class RegistroAsistencia(models.Model):
    class Tipo(models.TextChoices):
        PRESENTE = 'PRESENTE', 'Presente'
        AUSENTE = 'AUSENTE', 'Ausente'
        TARDANZA = 'TARDANZA', 'Tardanza'
        RETIRO_ANTICIPADO = 'RETIRO', 'Retiro anticipado'
        HORA_EXTRA = 'HEXTRA', 'Hora extra'
        FERIADO = 'FERIADO', 'Feriado / no laborable'
        HOME_OFFICE = 'HOME', 'Home office'
        VACACIONES = 'VACACIONES', 'Vacaciones'
        LICENCIA = 'LICENCIA', 'Licencia'

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

    def calcular_metricas_jornada(self):
        asignacion = (
            AsignacionJornada.objects.filter(empleado=self.empleado, jornada__activa=True)
            .select_related('jornada')
            .first()
        )
        jornada = asignacion.jornada if asignacion else (
            Jornada.objects.filter(es_predeterminada=True, activa=True).first()
        )
        if jornada and jornada.hora_entrada and jornada.hora_salida:
            hora_inicio = jornada.hora_entrada
            hora_fin = jornada.hora_salida
            tolerancia = jornada.tolerancia_minutos
        else:
            jornada = (
                Jornada.objects.filter(
                    empleado=self.empleado,
                    dia_semana=self.fecha.weekday(),
                    vigencia_desde__lte=self.fecha,
                    activa=True,
                    turno__activo=True,
                )
                .filter(
                    models.Q(vigencia_hasta__isnull=True)
                    | models.Q(vigencia_hasta__gte=self.fecha)
                )
                .select_related('turno')
                .order_by('-vigencia_desde')
                .first()
            )
            if jornada is None or jornada.turno is None:
                return
            hora_inicio = jornada.turno.hora_inicio
            hora_fin = jornada.turno.hora_fin
            tolerancia = jornada.turno.minutos_tolerancia

        if jornada is None:
            return

        inicio = hora_inicio.hour * 60 + hora_inicio.minute
        fin = hora_fin.hour * 60 + hora_fin.minute
        ingreso = self.hora_ingreso.hour * 60 + self.hora_ingreso.minute if self.hora_ingreso else None
        egreso = self.hora_egreso.hour * 60 + self.hora_egreso.minute if self.hora_egreso else None

        turno_nocturno = fin <= inicio
        if turno_nocturno:
            fin += 24 * 60
        if turno_nocturno and ingreso is not None and ingreso < inicio:
            ingreso += 24 * 60
        if turno_nocturno and egreso is not None and egreso < inicio:
            egreso += 24 * 60

        self.minutos_tardanza = (
            max(0, ingreso - inicio - tolerancia)
            if ingreso is not None else 0
        )
        self.minutos_extra = max(0, egreso - fin) if egreso is not None else 0

    def save(self, *args, **kwargs):
        if self.tipo not in (
            self.Tipo.FERIADO,
            self.Tipo.HOME_OFFICE,
            self.Tipo.HORA_EXTRA,
        ):
            self.calcular_metricas_jornada()
        super().save(*args, **kwargs)


class Marcacion(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SALIDA = 'SALIDA', 'Salida'

    class Origen(models.TextChoices):
        WEB = 'WEB', 'Web'
        IMPORTACION = 'IMPORTACION', 'Importación'
        MANUAL = 'MANUAL', 'Manual'

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='marcaciones',
    )
    fecha_hora = models.DateTimeField()
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    origen = models.CharField(max_length=15, choices=Origen.choices, default=Origen.MANUAL)
    ip = models.GenericIPAddressField(null=True, blank=True)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marcaciones_cargadas',
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_hora']
        constraints = [
            models.UniqueConstraint(
                fields=['empleado', 'fecha_hora'],
                name='asistencia_marcacion_empleado_fecha_hora_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['empleado', 'fecha_hora'], name='asist_marca_emp_fecha_idx'),
        ]

    def __str__(self):
        return (
            f'{self.empleado.legajo} | {self.fecha_hora:%Y-%m-%d %H:%M} '
            f'| {self.get_tipo_display()}'
        )
