"""Emisión de certificados de capacitación en el legajo del empleado."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.empleados.models import CategoriaDocumento, DocumentoLegajo, HistorialLaboral
from apps.empleados.services import registrar_movimiento

from .models import AsistenciaCapacitacion, Certificado, Inscripcion


@transaction.atomic
def emitir_certificado(inscripcion_id, archivo, usuario, titulo='Certificado de capacitación'):
    inscripcion = Inscripcion.objects.select_for_update().select_related(
        'empleado', 'curso'
    ).get(pk=inscripcion_id)
    if inscripcion.estado == Inscripcion.Estado.CANCELADO:
        raise ValidationError('No se puede certificar una inscripción cancelada.')
    if inscripcion.curso.fecha_fin > timezone.localdate():
        raise ValidationError('El certificado solo se puede emitir cuando el curso haya finalizado.')
    total_asistencias = AsistenciaCapacitacion.objects.filter(
        inscripcion=inscripcion,
    ).count()
    presentes = AsistenciaCapacitacion.objects.filter(
        inscripcion=inscripcion, presente=True,
    ).count()
    porcentaje = (
        Decimal(presentes) * Decimal('100') / Decimal(inscripcion.curso.sesiones)
    )
    if total_asistencias < inscripcion.curso.sesiones:
        raise ValidationError('Registra la asistencia de todas las sesiones antes de certificar.')
    if porcentaje < inscripcion.curso.asistencia_minima:
        raise ValidationError(
            f'La asistencia ({porcentaje:.2f}%) no alcanza el mínimo '
            f'requerido ({inscripcion.curso.asistencia_minima}%).'
        )
    if hasattr(inscripcion, 'certificado'):
        raise ValidationError('Esta inscripción ya tiene un certificado.')

    categoria, _ = CategoriaDocumento.objects.get_or_create(
        nombre='Certificados de capacitación',
        defaults={'descripcion': 'Certificados de cursos y actividades de capacitación.'},
    )
    documento = DocumentoLegajo.objects.create(
        empleado=inscripcion.empleado,
        categoria=categoria,
        titulo=titulo or f'Certificado: {inscripcion.curso.nombre}',
        descripcion=(
            f'Curso: {inscripcion.curso.nombre}. '
            f'Emitido al completar {porcentaje:.2f}% de asistencia.'
        ),
        archivo=archivo,
        fecha_emision=timezone.localdate(),
        fecha_presentacion=timezone.localdate(),
        cargado_por=usuario,
    )
    certificado = Certificado.objects.create(
        inscripcion=inscripcion,
        documento_legajo=documento,
    )
    inscripcion.estado = Inscripcion.Estado.COMPLETADO
    inscripcion.save(update_fields=['estado'])
    registrar_movimiento(
        empleado=inscripcion.empleado,
        fecha=timezone.localdate(),
        tipo_movimiento=HistorialLaboral.TipoMovimiento.CAPACITACION,
        descripcion=f'Completó el curso "{inscripcion.curso.nombre}" y recibió un certificado.',
        usuario=usuario,
        referencia_app='capacitaciones',
        referencia_id=certificado.pk,
    )
    return certificado
