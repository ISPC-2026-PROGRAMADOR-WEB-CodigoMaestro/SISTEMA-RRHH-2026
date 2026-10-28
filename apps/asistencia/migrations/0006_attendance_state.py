import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asistencia', '0005_alter_registroasistencia_tipo'),
        ('horarios_laborales', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='registroasistencia',
            name='estado',
            field=models.CharField(
                choices=[
                    ('PUNTUAL', 'Puntual'),
                    ('TARDE', 'Tarde'),
                    ('AUSENTE', 'Ausente'),
                    ('FRANCO_TRABAJADO', 'Franco trabajado'),
                    ('FERIADO_TRABAJADO', 'Feriado trabajado'),
                    ('SIN_HORARIO', 'Sin horario'),
                ],
                default='SIN_HORARIO',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='registroasistencia',
            name='horario_diario',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='registros_asistencia',
                to='horarios_laborales.horariodiario',
            ),
        ),
    ]
