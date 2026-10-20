"""Vistas web de autoservicio e importación de asistencia."""
import csv
import io
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.accounts.permissions import rol_de
from apps.empleados.models import Empleado

from .models import Marcacion
from .services import cerrar_dia, importar_marcaciones, registrar_marcacion


def _puede_operar(user):
    return rol_de(user) in ('GERENTE', 'ADMINISTRATIVO')


def fichar(request):
    """Permite registrar llegada o salida identificando al empleado por legajo."""
    hoy = timezone.localdate()
    legajo_ingresado = (
        request.POST.get('legajo', '').strip()
        if request.method == 'POST'
        else request.GET.get('legajo', '').strip()
    )
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if not legajo_ingresado:
            messages.error(request, 'Ingresa tu número de legajo.')
        elif accion not in ('llegada', 'salida'):
            messages.error(request, 'Selecciona Llegada o Salida.')
        else:
            tipo = (
                Marcacion.Tipo.ENTRADA
                if accion == 'llegada'
                else Marcacion.Tipo.SALIDA
            )
            try:
                empleado = Empleado.objects.get(
                    legajo__iexact=legajo_ingresado,
                    estado=Empleado.Estado.ACTIVO,
                )
            except Empleado.DoesNotExist:
                messages.error(
                    request,
                    'No se encontró un empleado activo con ese número de legajo.',
                )
                return redirect('asistencia:fichar')
            try:
                marcacion = registrar_marcacion(
                    empleado,
                    Marcacion.Origen.WEB,
                    ip=request.META.get('REMOTE_ADDR'),
                    tipo=tipo,
                )
            except ValidationError as exc:
                errores = (
                    [str(error) for values in exc.message_dict.values() for error in values]
                    if hasattr(exc, 'message_dict') else exc.messages
                )
                messages.error(request, ' '.join(errores))
            else:
                messages.success(
                    request,
                    f'{marcacion.get_tipo_display()} registrada correctamente.',
                )
        return redirect('asistencia:fichar')

    return render(request, 'asistencia/fichar.html', {
        'hoy': hoy,
        'zona_horaria': timezone.get_current_timezone_name(),
        'legajo_ingresado': legajo_ingresado,
    })


@login_required
@require_POST
def cerrar_hoy(request):
    """Finaliza manualmente el día actual desde el panel de asistencia."""
    if not _puede_operar(request.user):
        raise PermissionDenied('Se requiere rol Gerente o Administrativo.')

    fecha = timezone.localdate()
    resumen = cerrar_dia(fecha)
    messages.success(
        request,
        f'Día terminado ({fecha}): {resumen["consolidados"]} consolidados, '
        f'{resumen["ausentes_creados"]} ausentes y '
        f'{resumen["licencias_creadas"]} licencias/vacaciones generadas.',
    )
    return redirect('web:modulo', slug='asistencia')


@login_required
def importar(request):
    """Importa marcaciones y permite ejecutar el cierre diario."""
    if not _puede_operar(request.user):
        raise PermissionDenied('Se requiere rol Gerente o Administrativo.')

    resumen = None
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'importar':
            archivo = request.FILES.get('archivo')
            if not archivo:
                messages.error(request, 'Selecciona un archivo CSV o XLSX.')
            else:
                try:
                    resumen = importar_marcaciones(archivo, request.user)
                except ValidationError as exc:
                    errores = (
                        [str(error) for values in exc.message_dict.values() for error in values]
                        if hasattr(exc, 'message_dict') else exc.messages
                    )
                    messages.error(request, ' '.join(errores))
                else:
                    resumen['tipo'] = 'importacion'
                    messages.success(
                        request,
                        f"Importación terminada: {resumen['creadas']} creadas, "
                        f"{resumen['duplicadas']} duplicadas.",
                    )
        elif accion == 'cerrar':
            fecha_texto = request.POST.get('fecha')
            try:
                fecha = date.fromisoformat(fecha_texto) if fecha_texto else (
                    timezone.localdate() - timedelta(days=1)
                )
            except ValueError:
                messages.error(request, 'La fecha debe tener formato YYYY-MM-DD.')
            else:
                resumen = cerrar_dia(fecha)
                resumen['fecha'] = fecha
                resumen['tipo'] = 'cierre'
                messages.success(
                    request,
                    f"Cierre completo: {resumen['consolidados']} consolidados, "
                    f"{resumen['ausentes_creados']} ausencias y "
                    f"{resumen['licencias_creadas']} licencias/vacaciones creadas.",
                )

    return render(request, 'asistencia/importar.html', {'resumen': resumen})


@login_required
def ejemplo_csv(request):
    """Descarga un CSV mínimo compatible con la importación."""
    if not _puede_operar(request.user):
        raise PermissionDenied('Se requiere rol Gerente o Administrativo.')
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(['legajo', 'fecha', 'hora', 'tipo'])
    escritor.writerow(['EMP-001', '15/10/2026', '09:00', 'ENTRADA'])
    escritor.writerow(['EMP-001', '15/10/2026', '18:00', 'SALIDA'])
    respuesta = HttpResponse(salida.getvalue(), content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = 'attachment; filename="ejemplo_marcaciones.csv"'
    return respuesta
