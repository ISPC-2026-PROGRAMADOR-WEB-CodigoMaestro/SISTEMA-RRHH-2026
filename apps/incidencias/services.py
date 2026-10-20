"""Reglas para el flujo de estados de incidencias."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Incidencia

TRANSICIONES = {
    Incidencia.Estado.ABIERTA: {
        Incidencia.Estado.ASIGNADA,
        Incidencia.Estado.EN_ANALISIS,
    },
    Incidencia.Estado.ASIGNADA: {
        Incidencia.Estado.EN_ANALISIS,
        Incidencia.Estado.PENDIENTE_DOC,
        Incidencia.Estado.RESUELTA,
    },
    Incidencia.Estado.EN_ANALISIS: {
        Incidencia.Estado.PENDIENTE_DOC,
        Incidencia.Estado.RESUELTA,
    },
    Incidencia.Estado.PENDIENTE_DOC: {
        Incidencia.Estado.EN_ANALISIS,
        Incidencia.Estado.RESUELTA,
    },
    Incidencia.Estado.RESUELTA: {
        Incidencia.Estado.EN_ANALISIS,
        Incidencia.Estado.CERRADA,
    },
    Incidencia.Estado.CERRADA: set(),
}


@transaction.atomic
def cambiar_estado_incidencia(incidencia_id, nuevo_estado):
    incidencia = Incidencia.objects.select_for_update().get(pk=incidencia_id)
    if not isinstance(nuevo_estado, str) or nuevo_estado not in TRANSICIONES:
        raise ValidationError({'estado': 'El estado indicado no es válido.'})
    if nuevo_estado not in TRANSICIONES[incidencia.estado]:
        raise ValidationError({
            'estado': (
                f'No se puede cambiar de {incidencia.get_estado_display()} '
                f'a {dict(Incidencia.Estado.choices)[nuevo_estado]}.'
            )
        })
    if nuevo_estado == Incidencia.Estado.ASIGNADA and not incidencia.responsable_id:
        raise ValidationError({'responsable': 'Asigna un responsable antes de pasar a asignada.'})
    incidencia.estado = nuevo_estado
    incidencia.fecha_resolucion = (
        timezone.now() if nuevo_estado == Incidencia.Estado.RESUELTA
        else None if nuevo_estado == Incidencia.Estado.EN_ANALISIS
        else incidencia.fecha_resolucion
    )
    incidencia.save(update_fields=['estado', 'fecha_resolucion', 'fecha_actualizacion'])
    return incidencia
