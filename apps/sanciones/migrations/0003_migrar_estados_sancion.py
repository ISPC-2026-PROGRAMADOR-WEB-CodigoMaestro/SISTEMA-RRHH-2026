from django.db import migrations


def migrar_estados(apps, schema_editor):
    Sancion = apps.get_model('sanciones', 'Sancion')
    Sancion.objects.filter(estado='EN_REVISION').update(estado='PROPUESTA')
    Sancion.objects.filter(estado='FIRME').update(estado='APLICADA')
    Sancion.objects.filter(estado='FINALIZADA').update(estado='APLICADA')


class Migration(migrations.Migration):
    dependencies = [
        ('sanciones', '0002_sancion_fecha_apelacion_sancion_fecha_aplicacion_and_more'),
    ]

    operations = [migrations.RunPython(migrar_estados, migrations.RunPython.noop)]
