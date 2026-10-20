"""Cálculo y transiciones de evaluaciones de desempeño."""
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.empleados.models import HistorialLaboral
from apps.empleados.services import registrar_movimiento

from .models import DetalleEvaluacion, EvaluacionDesempeno


def calcular_puntaje_ponderado(detalles):
    puntaje_ponderado = Decimal('0')
    suma_pesos = Decimal('0')
    for detalle in detalles:
        criterio = detalle['criterio'] if isinstance(detalle, dict) else detalle.criterio
        calificacion = (
            detalle['calificacion'] if isinstance(detalle, dict)
            else detalle.calificacion
        )
        if not 0 <= Decimal(calificacion) <= 100:
            raise ValidationError('Las calificaciones deben estar entre 0 y 100.')
        if criterio.peso <= 0:
            raise ValidationError(f'El criterio "{criterio.nombre}" debe tener peso mayor que cero.')
        puntaje_ponderado += Decimal(calificacion) * criterio.peso
        suma_pesos += criterio.peso

    if not suma_pesos:
        return None
    return (puntaje_ponderado / suma_pesos).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP,
    )


def recalcular_puntaje(evaluacion):
    detalles = list(
        evaluacion.detalles.select_related('criterio').all()
    )
    evaluacion.calificacion_general = calcular_puntaje_ponderado(detalles)
    evaluacion.save(update_fields=['calificacion_general', 'fecha_actualizacion'])
    return evaluacion.calificacion_general


@transaction.atomic
def cambiar_estado_evaluacion(evaluacion_id, accion, usuario):
    evaluacion = EvaluacionDesempeno.objects.select_for_update().select_related(
        'empleado', 'periodo'
    ).get(pk=evaluacion_id)
    estados = {
        'iniciar': (EvaluacionDesempeno.Estado.BORRADOR, EvaluacionDesempeno.Estado.EN_CURSO),
        'finalizar': (EvaluacionDesempeno.Estado.EN_CURSO, EvaluacionDesempeno.Estado.FINALIZADA),
    }
    if accion == 'anular':
        if evaluacion.estado not in (
            EvaluacionDesempeno.Estado.BORRADOR,
            EvaluacionDesempeno.Estado.EN_CURSO,
        ):
            raise ValidationError('Solo se puede anular una evaluación en borrador o en curso.')
        evaluacion.estado = EvaluacionDesempeno.Estado.ANULADA
    else:
        if accion not in estados:
            raise ValidationError('La acción solicitada no es válida.')
        origen, destino = estados[accion]
        if evaluacion.estado != origen:
            raise ValidationError(
                f'No se puede {accion} una evaluación en estado {evaluacion.get_estado_display()}.'
            )
        evaluacion.estado = destino

    if evaluacion.estado == EvaluacionDesempeno.Estado.FINALIZADA:
        puntaje = recalcular_puntaje(evaluacion)
        if puntaje is None:
            raise ValidationError('Agrega al menos un criterio calificado antes de finalizar.')
        registrar_movimiento(
            empleado=evaluacion.empleado,
            fecha=evaluacion.fecha_evaluacion or timezone.localdate(),
            tipo_movimiento=HistorialLaboral.TipoMovimiento.EVALUACION,
            descripcion=(
                f'Evaluación de desempeño "{evaluacion.periodo.nombre}" finalizada '
                f'con puntaje ponderado {puntaje}/100.'
            ),
            usuario=usuario,
            referencia_app='evaluaciones',
            referencia_id=evaluacion.pk,
        )
    evaluacion.save(update_fields=['estado', 'fecha_actualizacion'])
    return evaluacion


def comparar_con_periodo_anterior(evaluacion):
    if evaluacion.estado != EvaluacionDesempeno.Estado.FINALIZADA:
        raise ValidationError('Solo se pueden comparar evaluaciones finalizadas.')
    anterior = (
        EvaluacionDesempeno.objects.filter(
            empleado=evaluacion.empleado,
            estado=EvaluacionDesempeno.Estado.FINALIZADA,
            periodo__fecha_fin__lt=evaluacion.periodo.fecha_inicio,
        )
        .exclude(pk=evaluacion.pk)
        .select_related('periodo')
        .order_by('-periodo__fecha_fin')
        .first()
    )
    if anterior is None:
        return None
    return {
        'periodo_anterior': anterior.periodo.nombre,
        'puntaje_anterior': anterior.calificacion_general,
        'periodo_actual': evaluacion.periodo.nombre,
        'puntaje_actual': evaluacion.calificacion_general,
        'variacion': (
            evaluacion.calificacion_general - anterior.calificacion_general
            if evaluacion.calificacion_general is not None
            and anterior.calificacion_general is not None
            else None
        ),
    }
