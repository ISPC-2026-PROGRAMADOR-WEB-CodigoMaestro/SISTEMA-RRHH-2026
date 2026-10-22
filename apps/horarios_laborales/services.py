from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.asistencia.services import (
    LIMITE_ARCHIVO,
    _leer_archivo,
    _normalizar_cabecera,
)
from apps.empleados.models import Empleado
from .models import HorarioPredeterminado

LIMITE_FILAS_HORARIOS = 1000
MAX_LONGITUD_OBSERVACIONES = 1000


def _parsear_fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or '').strip()
    for formato in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError('fecha inválida; usa AAAA-MM-DD o DD/MM/AAAA')


def _parsear_hora(valor):
    if valor is None or str(valor).strip() == '':
        return None
    if hasattr(valor, 'hour') and hasattr(valor, 'minute'):
        hora = valor.replace(second=0, microsecond=0)
        return hora.time() if isinstance(hora, datetime) else hora
    texto = str(valor).strip()
    for formato in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(texto, formato).time()
        except ValueError:
            continue
    raise ValueError('hora inválida; usa HH:MM')


def _parsear_franco(valor):
    texto = _normalizar_cabecera(valor).lower()
    if texto in ('', '0', 'no', 'false', 'n', 'trabaja'):
        return False
    if texto in ('1', 'si', 's', 'true', 'franco'):
        return True
    raise ValueError('es_franco debe ser Sí/No o True/False')


def parsear_archivo_horarios(archivo):
    if getattr(archivo, 'size', 0) > LIMITE_ARCHIVO:
        raise ValidationError('El archivo no puede superar los 5 MB.')
    cabecera, filas = _leer_archivo(archivo)
    if len(filas) > LIMITE_FILAS_HORARIOS:
        raise ValidationError(
            f'El archivo no puede contener más de {LIMITE_FILAS_HORARIOS} filas.'
        )

    indices = {
        _normalizar_cabecera(nombre): indice
        for indice, nombre in enumerate(cabecera)
    }
    requeridas = {'legajo', 'fecha', 'hora_entrada', 'hora_salida'}
    faltantes = requeridas - indices.keys()
    if faltantes:
        raise ValidationError(
            f'Faltan columnas obligatorias: {", ".join(sorted(faltantes))}.'
        )

    filas_validas = []
    errores = []
    legajos = set()
    identidades = set()
    for numero, fila in enumerate(filas, start=2):
        if not any(str(celda or '').strip() for celda in fila):
            continue

        def valor(nombre):
            indice = indices.get(nombre)
            return fila[indice] if indice is not None and indice < len(fila) else None

        legajo = str(valor('legajo') or '').strip()
        try:
            if not legajo:
                raise ValueError('falta el legajo')
            fecha = _parsear_fecha(valor('fecha'))
            es_franco = _parsear_franco(valor('es_franco'))
            hora_entrada = _parsear_hora(valor('hora_entrada'))
            hora_salida = _parsear_hora(valor('hora_salida'))
            observaciones = str(valor('observaciones') or '').strip()
            if len(observaciones) > MAX_LONGITUD_OBSERVACIONES:
                raise ValueError('observaciones supera 1000 caracteres')
            if es_franco:
                if hora_entrada is not None or hora_salida is not None:
                    raise ValueError('un franco debe tener horas de entrada y salida vacías')
            elif hora_entrada is None or hora_salida is None:
                raise ValueError('entrada y salida son obligatorias si no es franco')
            identidad = (legajo, fecha.isoformat())
            if identidad in identidades:
                raise ValueError('empleado y fecha están repetidos dentro del archivo')
            identidades.add(identidad)
            filas_validas.append({
                'fila': numero,
                'legajo': legajo,
                'fecha': fecha.isoformat(),
                'hora_entrada': hora_entrada.isoformat() if hora_entrada else '',
                'hora_salida': hora_salida.isoformat() if hora_salida else '',
                'es_franco': es_franco,
                'observaciones': observaciones,
            })
            legajos.add(legajo)
        except (TypeError, ValueError, OverflowError) as exc:
            errores.append({'fila': numero, 'motivo': str(exc)})

    if not filas_validas and not errores:
        raise ValidationError('El archivo no contiene filas de horarios.')

    empleados = {
        empleado.legajo: empleado
        for empleado in Empleado.objects.filter(legajo__in=legajos)
    }
    for fila in filas_validas[:]:
        empleado = empleados.get(fila['legajo'])
        if empleado is None:
            errores.append({
                'fila': fila['fila'],
                'motivo': f"no existe el legajo {fila['legajo']}",
            })
            filas_validas.remove(fila)
            continue
        fila['empleado_id'] = empleado.pk
        fila['empleado_nombre'] = empleado.nombre_completo

    return filas_validas, [
        f"Fila {error['fila']}: {error['motivo']}"
        for error in sorted(errores, key=lambda error: error['fila'])
    ]


@transaction.atomic
def establecer_horario_predeterminado(
    empleado,
    fecha,
    hora_entrada,
    hora_salida,
    observaciones='',
    usuario=None,
):
    if hora_entrada is None or hora_salida is None:
        raise ValidationError(
            'El horario predeterminado requiere entrada y salida.'
        )
    horario = HorarioPredeterminado.objects.select_for_update().filter(
        empleado=empleado,
        vigente_desde=fecha,
    ).first()
    es_nuevo = horario is None
    if es_nuevo:
        horario = HorarioPredeterminado(
            empleado=empleado,
            vigente_desde=fecha,
            creado_por=usuario,
        )
    horario.hora_entrada = hora_entrada
    horario.hora_salida = hora_salida
    horario.observaciones = observaciones
    horario.full_clean()
    HorarioPredeterminado.objects.filter(
        empleado=empleado,
        vigente_desde__gt=fecha,
    ).delete()
    horario.save()
    return horario
