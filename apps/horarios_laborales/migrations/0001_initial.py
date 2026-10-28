import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empleados', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionAsistencia',
            fields=[
                (
                    'id',
                    models.PositiveSmallIntegerField(
                        default=1,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'tolerancia_tardanza_minutos',
                    models.PositiveIntegerField(default=10),
                ),
                ('minimo_extra_minutos', models.PositiveIntegerField(default=30)),
            ],
            options={
                'verbose_name': 'configuración de asistencia',
                'verbose_name_plural': 'configuración de asistencia',
            },
        ),
        migrations.CreateModel(
            name='HorarioDiario',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('fecha', models.DateField()),
                ('hora_entrada', models.TimeField(blank=True, null=True)),
                ('hora_salida', models.TimeField(blank=True, null=True)),
                ('es_franco', models.BooleanField(default=False)),
                ('observaciones', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('modificado_en', models.DateTimeField(auto_now=True)),
                (
                    'creado_por',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='horarios_diarios_creados',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'empleado',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='horarios_diarios',
                        to='empleados.empleado',
                    ),
                ),
            ],
            options={
                'ordering': ['-fecha', 'empleado__apellido', 'empleado__nombre'],
            },
        ),
        migrations.AddConstraint(
            model_name='horariodiario',
            constraint=models.UniqueConstraint(
                fields=('empleado', 'fecha'),
                name='asist_horario_emp_fecha_uniq',
            ),
        ),
        migrations.AddIndex(
            model_name='horariodiario',
            index=models.Index(
                fields=['empleado', 'fecha'],
                name='asist_horario_emp_fecha_idx',
            ),
        ),
    ]
