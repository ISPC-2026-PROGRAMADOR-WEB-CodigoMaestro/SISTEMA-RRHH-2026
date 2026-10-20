"""Servicios compartidos para registrar movimientos de vida laboral."""
from apps.empleados.models import HistorialLaboral


def registrar_movimiento(
    *,
    empleado,
    fecha,
    tipo_movimiento,
    descripcion,
    usuario=None,
    observaciones='',
    referencia_app='',
    referencia_id=None,
):
    return HistorialLaboral.objects.create(
        empleado=empleado,
        fecha=fecha,
        tipo_movimiento=tipo_movimiento,
        descripcion=descripcion,
        usuario=usuario,
        observaciones=observaciones,
        referencia_app=referencia_app,
        referencia_id=referencia_id,
    )
