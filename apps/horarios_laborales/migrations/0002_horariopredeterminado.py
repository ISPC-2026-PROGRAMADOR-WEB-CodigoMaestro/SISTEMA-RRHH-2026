import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empleados', '0001_initial'),
        ('horarios_laborales', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HorarioPredeterminado',
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
                ('vigente_desde', models.DateField()),
                ('hora_entrada', models.TimeField()),
                ('hora_salida', models.TimeField()),
                ('observaciones', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                (
                    'creado_por',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='horarios_predeterminados_creados',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'empleado',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='horarios_predeterminados',
                        to='empleados.empleado',
                    ),
                ),
            ],
            options={
                'ordering': ['empleado_id', '-vigente_desde'],
            },
        ),
        migrations.AddConstraint(
            model_name='horariopredeterminado',
            constraint=models.UniqueConstraint(
                fields=('empleado', 'vigente_desde'),
                name='horario_pred_emp_vigencia_uniq',
            ),
        ),
        migrations.AddIndex(
            model_name='horariopredeterminado',
            index=models.Index(
                fields=['empleado', 'vigente_desde'],
                name='horario_pred_emp_vig_idx',
            ),
        ),
    ]
