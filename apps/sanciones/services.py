"""Transiciones y trazabilidad de sanciones."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.permissions import rol_de
from apps.empleados.models import HistorialLaboral
from apps.empleados.services import registrar_movimiento

from .models import Sancion


@transaction.atomic
def transicionar_sancion(sancion_id, accion, usuario, observacion=''):
    sancion = Sancion.objects.select_for_update().select_related('empleado').get(pk=sancion_id)
    rol = rol_de(usuario)
    transiciones = {
        'notificar': (Sancion.Estado.PROPUESTA, Sancion.Estado.NOTIFICADA),
        'aplicar': (Sancion.Estado.NOTIFICADA, Sancion.Estado.APLICADA),
        'apelar': (Sancion.Estado.NOTIFICADA, Sancion.Estado.APELADA),
        'resolver_apelacion': (Sancion.Estado.APELADA, Sancion.Estado.APLICADA),
    }
    if accion not in transiciones:
        raise ValidationError('La acción solicitada no es válida.')
    origen, destino = transiciones[accion]
    if sancion.estado != origen:
        raise ValidationError(
            f'No se puede {accion} una sanción en estado {sancion.get_estado_display()}.'
        )

    if accion == 'apelar':
        empleado_vinculado = getattr(usuario, 'empleado', None)
        if rol != 'GERENTE' and (
            empleado_vinculado is None or empleado_vinculado.pk != sancion.empleado_id
        ):
            raise PermissionDenied('Solo el empleado sancionado o un gerente puede apelar.')
    elif accion == 'notificar':
        if rol not in ('GERENTE', 'ADMINISTRATIVO'):
            raise PermissionDenied('Solo RR. HH. puede notificar la sanción.')
    elif rol != 'GERENTE':
        raise PermissionDenied('Esta transición requiere el rol Gerente.')

    sancion.estado = destino
    ahora = timezone.now()
    if destino == Sancion.Estado.NOTIFICADA:
        sancion.fecha_notificacion = ahora
    elif destino == Sancion.Estado.APLICADA:
        sancion.fecha_aplicacion = ahora
    elif destino == Sancion.Estado.APELADA:
        sancion.fecha_apelacion = ahora
        sancion.descargo_trabajador = observacion or sancion.descargo_trabajador
    sancion.save()

    if destino in (Sancion.Estado.APLICADA, Sancion.Estado.APELADA):
        registrar_movimiento(
            empleado=sancion.empleado,
            fecha=timezone.localdate(),
            tipo_movimiento=HistorialLaboral.TipoMovimiento.SANCION,
            descripcion=(
                f'Sanción {sancion.pk}: {sancion.get_tipo_display()} '
                f'({sancion.get_estado_display()}).'
            ),
            usuario=usuario,
            observaciones=observacion,
            referencia_app='sanciones',
            referencia_id=sancion.pk,
        )
    return sancion
