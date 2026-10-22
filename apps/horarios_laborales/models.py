from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class HorarioDiario(models.Model):
    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='horarios_diarios',
    )
    fecha = models.DateField()
    hora_entrada = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
    es_franco = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='horarios_diarios_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', 'empleado__apellido', 'empleado__nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['empleado', 'fecha'],
                name='asist_horario_emp_fecha_uniq',
            ),
        ]
        indexes = [
            models.Index(
                fields=['empleado', 'fecha'],
                name='asist_horario_emp_fecha_idx',
            ),
        ]

    def clean(self):
        super().clean()
        if self.es_franco:
            if self.hora_entrada is not None or self.hora_salida is not None:
                raise ValidationError({
                    'hora_entrada': 'Un día franco no puede tener horario.',
                    'hora_salida': 'Un día franco no puede tener horario.',
                })
        elif self.hora_entrada is None or self.hora_salida is None:
            raise ValidationError({
                'hora_entrada': 'La entrada y la salida son obligatorias si no es franco.',
                'hora_salida': 'La entrada y la salida son obligatorias si no es franco.',
            })

    def __str__(self):
        return f'{self.empleado} - {self.fecha}'


class HorarioPredeterminado(models.Model):
    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='horarios_predeterminados',
    )
    vigente_desde = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField()
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='horarios_predeterminados_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['empleado_id', '-vigente_desde']
        constraints = [
            models.UniqueConstraint(
                fields=['empleado', 'vigente_desde'],
                name='horario_pred_emp_vigencia_uniq',
            ),
        ]
        indexes = [
            models.Index(
                fields=['empleado', 'vigente_desde'],
                name='horario_pred_emp_vig_idx',
            ),
        ]

    def __str__(self):
        return (
            f'{self.empleado} - desde {self.vigente_desde} '
            f'({self.hora_entrada:%H:%M}-{self.hora_salida:%H:%M})'
        )


class ConfiguracionAsistencia(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    tolerancia_tardanza_minutos = models.PositiveIntegerField(default=10)
    minimo_extra_minutos = models.PositiveIntegerField(default=30)

    @classmethod
    def obtener(cls):
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'configuración de asistencia'
        verbose_name_plural = 'configuración de asistencia'

    def __str__(self):
        return 'Configuración de asistencia'
