"""Registro automático de nuevas sanciones en el historial laboral."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.empleados.models import HistorialLaboral
from apps.empleados.services import registrar_movimiento

from .models import Sancion


@receiver(post_save, sender=Sancion)
def registrar_sancion_en_historial(sender, instance, created, **kwargs):
    if not created:
        return
    registrar_movimiento(
        empleado=instance.empleado,
        fecha=instance.fecha_hecho or timezone.localdate(),
        tipo_movimiento=HistorialLaboral.TipoMovimiento.SANCION,
        descripcion=(
            f'Se registró una propuesta de sanción {instance.pk}: '
            f'{instance.get_tipo_display()}.'
        ),
        usuario=instance.responsable,
        observaciones=instance.descripcion,
        referencia_app='sanciones',
        referencia_id=instance.pk,
    )
