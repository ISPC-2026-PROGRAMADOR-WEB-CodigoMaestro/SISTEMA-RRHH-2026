"""Reglas de negocio para solicitudes de licencia y saldos vacacionales."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.empleados.models import HistorialLaboral
from apps.empleados.services import registrar_movimiento

from .models import SaldoVacaciones, SolicitudLicencia

ESTADOS_QUE_RESERVAN_FECHAS = (
    SolicitudLicencia.Estado.PENDIENTE,
    SolicitudLicencia.Estado.APROBADA,
)


def calcular_dias_habiles(fecha_inicio, fecha_fin):
    """Cuenta los días lunes-viernes del intervalo, sin feriados registrados."""
    if fecha_inicio > fecha_fin:
        raise ValidationError({'fecha_fin': 'La fecha de fin no puede ser anterior al inicio.'})

    from apps.asistencia.models import Feriado

    feriados = set(
        Feriado.objects.filter(
            fecha__range=(fecha_inicio, fecha_fin)
        ).values_list('fecha', flat=True)
    )
    dias = 0
    fecha = fecha_inicio
    while fecha <= fecha_fin:
        if fecha.weekday() < 5 and fecha not in feriados:
            dias += 1
        fecha += timedelta(days=1)
    return Decimal(dias)


def dias_vacaciones_por_antiguedad(empleado, anio):
    """Calcula el derecho anual al 31 de diciembre (escala laboral 14/21/28/35)."""
    ingreso = empleado.fecha_ingreso
    cierre = date(anio, 12, 31)
    if ingreso > cierre:
        return Decimal('0')
    antiguedad = cierre.year - ingreso.year - (
        (cierre.month, cierre.day) < (ingreso.month, ingreso.day)
    )
    if antiguedad < 5:
        dias = 14
    elif antiguedad < 10:
        dias = 21
    elif antiguedad < 20:
        dias = 28
    else:
        dias = 35
    return Decimal(dias)


def validar_solicitud(empleado, tipo_licencia, fecha_inicio, fecha_fin, excluir_id=None):
    """Valida rango, días máximos y solapamiento con otra solicitud vigente."""
    if fecha_inicio > fecha_fin:
        raise ValidationError({'fecha_fin': 'La fecha de fin no puede ser anterior al inicio.'})
    if not tipo_licencia.activo:
        raise ValidationError({'tipo_licencia': 'Este tipo de licencia no está habilitado.'})

    dias = calcular_dias_habiles(fecha_inicio, fecha_fin)
    if dias <= 0:
        raise ValidationError({'fecha_inicio': 'El rango debe incluir al menos un día hábil.'})
    if tipo_licencia.dias_maximos is not None and dias > tipo_licencia.dias_maximos:
        raise ValidationError({
            'fecha_fin': f'La licencia permite un máximo de {tipo_licencia.dias_maximos} días hábiles.'
        })

    solicitudes = SolicitudLicencia.objects.filter(
        empleado=empleado,
        estado__in=ESTADOS_QUE_RESERVAN_FECHAS,
        fecha_inicio__lte=fecha_fin,
        fecha_fin__gte=fecha_inicio,
    )
    if excluir_id is not None:
        solicitudes = solicitudes.exclude(pk=excluir_id)
    if solicitudes.exists():
        raise ValidationError('El empleado ya tiene una licencia pendiente o aprobada que se solapa.')
    return dias


def _dias_por_anio(fecha_inicio, fecha_fin):
    dias = {}
    fecha = fecha_inicio
    while fecha <= fecha_fin:
        if fecha.weekday() < 5:
            dias[fecha.year] = dias.get(fecha.year, 0) + 1
        fecha += timedelta(days=1)
    if dias:
        from apps.asistencia.models import Feriado
        feriados = Feriado.objects.filter(
            fecha__range=(fecha_inicio, fecha_fin)
        ).values_list('fecha', flat=True)
        for feriado in feriados:
            if feriado.weekday() < 5:
                dias[feriado.year] -= 1
    return {anio: Decimal(cantidad) for anio, cantidad in dias.items() if cantidad}


def _obtener_saldo_bloqueado(empleado, anio):
    saldo, _ = SaldoVacaciones.objects.get_or_create(
        empleado=empleado,
        anio=anio,
        defaults={'dias_correspondientes': dias_vacaciones_por_antiguedad(empleado, anio)},
    )
    return SaldoVacaciones.objects.select_for_update().get(pk=saldo.pk)


def _actualizar_estado(solicitud, estado, usuario, observacion=''):
    solicitud.estado = estado
    solicitud.revisado_por = usuario
    solicitud.fecha_revision = timezone.now()
    solicitud.observacion_revision = observacion
    solicitud.save(update_fields=[
        'estado', 'dias_solicitados', 'dias_descontados', 'revisado_por',
        'fecha_revision', 'observacion_revision',
        'fecha_actualizacion',
    ])


@transaction.atomic
def aprobar_solicitud(solicitud_id, usuario, observacion=''):
    solicitud = SolicitudLicencia.objects.select_for_update().select_related(
        'empleado', 'tipo_licencia'
    ).get(pk=solicitud_id)
    if solicitud.estado != SolicitudLicencia.Estado.PENDIENTE:
        raise ValidationError('Solo se pueden aprobar solicitudes pendientes.')

    dias = validar_solicitud(
        solicitud.empleado,
        solicitud.tipo_licencia,
        solicitud.fecha_inicio,
        solicitud.fecha_fin,
        excluir_id=solicitud.pk,
    )
    dias_descontados = {}
    if solicitud.tipo_licencia.descuenta_vacaciones:
        dias_por_anio = _dias_por_anio(solicitud.fecha_inicio, solicitud.fecha_fin)
        for anio, dias_anio in dias_por_anio.items():
            saldo = _obtener_saldo_bloqueado(solicitud.empleado, anio)
            if saldo.dias_pendientes < dias_anio:
                raise ValidationError(
                    f'El saldo de vacaciones de {anio} es insuficiente '
                    f'({saldo.dias_pendientes} disponibles, {dias_anio} solicitados).'
                )
            saldo.dias_usados = F('dias_usados') + dias_anio
            saldo.save(update_fields=['dias_usados'])
            saldo.refresh_from_db(fields=['dias_usados'])
            dias_descontados[str(anio)] = str(dias_anio)

    solicitud.dias_solicitados = dias
    solicitud.dias_descontados = dias_descontados
    _actualizar_estado(solicitud, SolicitudLicencia.Estado.APROBADA, usuario, observacion)
    tipo_movimiento = (
        HistorialLaboral.TipoMovimiento.VACACIONES
        if solicitud.tipo_licencia.descuenta_vacaciones
        else HistorialLaboral.TipoMovimiento.LICENCIA
    )
    registrar_movimiento(
        empleado=solicitud.empleado,
        fecha=solicitud.fecha_inicio,
        tipo_movimiento=tipo_movimiento,
        descripcion=(
            f'{solicitud.tipo_licencia.nombre}: {solicitud.fecha_inicio} a '
            f'{solicitud.fecha_fin} ({dias} días hábiles), aprobada.'
        ),
        usuario=usuario,
        observaciones=observacion,
        referencia_app='licencias',
        referencia_id=solicitud.pk,
    )
    return solicitud


@transaction.atomic
def rechazar_solicitud(solicitud_id, usuario, observacion=''):
    solicitud = SolicitudLicencia.objects.select_for_update().select_related(
        'empleado'
    ).get(pk=solicitud_id)
    if solicitud.estado != SolicitudLicencia.Estado.PENDIENTE:
        raise ValidationError('Solo se pueden rechazar solicitudes pendientes.')
    _actualizar_estado(solicitud, SolicitudLicencia.Estado.RECHAZADA, usuario, observacion)
    return solicitud


@transaction.atomic
def cancelar_solicitud(solicitud_id, usuario, observacion=''):
    solicitud = SolicitudLicencia.objects.select_for_update().select_related(
        'empleado', 'tipo_licencia'
    ).get(pk=solicitud_id)
    if solicitud.estado not in (
        SolicitudLicencia.Estado.PENDIENTE,
        SolicitudLicencia.Estado.APROBADA,
    ):
        raise ValidationError('Solo se pueden cancelar solicitudes pendientes o aprobadas.')

    estaba_aprobada = solicitud.estado == SolicitudLicencia.Estado.APROBADA
    if estaba_aprobada and solicitud.tipo_licencia.descuenta_vacaciones:
        for anio, dias_anio in solicitud.dias_descontados.items():
            anio = int(anio)
            dias_anio = Decimal(str(dias_anio))
            saldo = _obtener_saldo_bloqueado(solicitud.empleado, anio)
            if saldo.dias_usados < dias_anio:
                raise ValidationError(
                    f'No se puede devolver el saldo de {anio}: el saldo usado no cubre '
                    'los días de esta solicitud.'
                )
            saldo.dias_usados = F('dias_usados') - dias_anio
            saldo.save(update_fields=['dias_usados'])

    _actualizar_estado(solicitud, SolicitudLicencia.Estado.CANCELADA, usuario, observacion)
    if estaba_aprobada:
        registrar_movimiento(
            empleado=solicitud.empleado,
            fecha=timezone.localdate(),
            tipo_movimiento=HistorialLaboral.TipoMovimiento.LICENCIA,
            descripcion=f'Se canceló la licencia {solicitud.pk} ({solicitud.fecha_inicio} a {solicitud.fecha_fin}).',
            usuario=usuario,
            observaciones=observacion,
            referencia_app='licencias',
            referencia_id=solicitud.pk,
        )
    return solicitud
