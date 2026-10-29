"""Vistas del dashboard web (Django templates + Bootstrap)."""
import secrets
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.asistencia.models import Feriado, RegistroAsistencia
from apps.asistencia.services import obtener_horario_esperado
from apps.empleados.models import Empleado
from apps.accounts.permissions import rol_de
from apps.horarios_laborales.models import (
    HorarioDiario,
    HorarioPredeterminado,
)
from apps.horarios_laborales.forms import HorarioDiarioForm
from apps.horarios_laborales.services import (
    establecer_horario_predeterminado,
    parsear_archivo_horarios,
)
from apps.incidencias.models import ComentarioIncidencia, Incidencia
from apps.licencias.models import SaldoVacaciones, SolicitudLicencia
from apps.licencias.services import cancelar_solicitud, dias_vacaciones_por_antiguedad
from apps.puestos.models import Puesto
from apps.sanciones.models import Sancion

from .forms import LicenciaAutogestionForm
from .forms_usuarios import UsuarioForm
from .registro import MODULOS, display

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('web:dashboard')
    error = None
    if request.method == 'POST':
        usuario = authenticate(
            request,
            username=request.POST.get('username', ''),
            password=request.POST.get('password', ''),
        )
        if usuario is not None:
            login(request, usuario)
            return redirect(request.GET.get('next') or 'web:dashboard')
        error = 'Usuario o contraseña incorrectos.'
    return render(request, 'web/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('web:login')


@login_required
def horarios_laborales(request):
    rol = rol_de(request.user)
    roles_con_acceso_general = ('GERENTE', 'ADMINISTRATIVO', 'LECTURA')
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if rol not in roles_con_acceso_general and empleado is None:
        raise PermissionDenied('El usuario no tiene un legajo de empleado vinculado.')

    horarios = HorarioDiario.objects.select_related('empleado')
    if rol not in roles_con_acceso_general:
        horarios = horarios.filter(empleado=empleado)

    puede_gestionar = rol in ('GERENTE', 'ADMINISTRATIVO')
    errores = []
    errores_carga = []
    filas_previsualizadas = []
    formulario = HorarioDiarioForm()
    if request.method == 'POST':
        if not puede_gestionar:
            raise PermissionDenied('Solo GERENTE o ADMINISTRATIVO puede cargar horarios.')
        accion = request.POST.get('accion')
        if accion == 'crear_individual':
            formulario = HorarioDiarioForm(request.POST)
            if formulario.is_valid():
                horario = formulario.save(commit=False)
                horario.creado_por = request.user
                try:
                    with transaction.atomic():
                        horario.full_clean()
                        horario.save()
                        tiene_predeterminado = (
                            HorarioPredeterminado.objects.filter(
                                empleado=horario.empleado,
                            ).exists()
                        )
                        establecer_predeterminado = (
                            formulario.cleaned_data['alcance']
                            == 'predeterminado'
                            or not tiene_predeterminado
                        )
                        if establecer_predeterminado and not horario.es_franco:
                            establecer_horario_predeterminado(
                                horario.empleado,
                                horario.fecha,
                                horario.hora_entrada,
                                horario.hora_salida,
                                horario.observaciones,
                                request.user,
                            )
                except (ValidationError, IntegrityError) as exc:
                    if isinstance(exc, ValidationError):
                        formulario.add_error(None, exc)
                    else:
                        formulario.add_error(
                            'fecha',
                            'Ya existe un horario para ese empleado y fecha.',
                        )
                else:
                    if establecer_predeterminado and not horario.es_franco:
                        mensaje = (
                            'El horario se guardó y quedó como predeterminado '
                            'desde esa fecha.'
                        )
                    else:
                        mensaje = (
                            'El horario se guardó solo para esa fecha; después '
                            'se aplicará el horario predeterminado.'
                        )
                    messages.success(request, mensaje)
                    return redirect('web:horarios_laborales')
        elif accion == 'previsualizar_archivo':
            archivo = request.FILES.get('archivo_horarios')
            if archivo is None:
                errores_carga.append('Selecciona un archivo CSV o XLSX.')
            else:
                filas = []
                try:
                    filas, errores_carga = parsear_archivo_horarios(archivo)
                except ValidationError as exc:
                    errores_carga.extend(exc.messages)
                if filas:
                    empleados_ids = {fila['empleado_id'] for fila in filas}
                    empleados_con_predeterminado = set(
                        HorarioPredeterminado.objects.filter(
                            empleado_id__in=empleados_ids,
                        ).values_list('empleado_id', flat=True).distinct()
                    )
                    primera_fecha_sin_predeterminado = {}
                    for fila in sorted(
                        filas,
                        key=lambda item: (item['empleado_id'], item['fecha']),
                    ):
                        empleado_id = fila['empleado_id']
                        if (
                            empleado_id not in empleados_con_predeterminado
                            and not fila['es_franco']
                        ):
                            primera_fecha_sin_predeterminado.setdefault(
                                empleado_id,
                                fila['fecha'],
                            )
                    for fila in filas:
                        fila['predeterminado_inicial'] = (
                            not fila['es_franco']
                            and primera_fecha_sin_predeterminado.get(
                                fila['empleado_id'],
                            ) == fila['fecha']
                        )
                    for indice, fila in enumerate(filas):
                        fila['indice'] = indice
                    request.session['horarios_laborales_preview'] = {
                        'token': secrets.token_urlsafe(18),
                        'filas': filas,
                        'errores': errores_carga,
                    }
                    return redirect('web:horarios_laborales')
        elif accion == 'confirmar_archivo':
            preview = request.session.get('horarios_laborales_preview')
            if (
                not preview
                or request.POST.get('token') != preview.get('token')
            ):
                errores_carga.append(
                    'La vista previa expiró o no es válida. Vuelve a cargar el archivo.'
                )
            else:
                errores_carga.extend(preview.get('errores', []))
                creados = reemplazados = omitidos = 0
                predeterminados_actualizados = 0
                filas = sorted(
                    preview.get('filas', []),
                    key=lambda fila: (fila['empleado_id'], fila['fecha']),
                )
                with transaction.atomic():
                    for fila in filas:
                        indice = fila['indice']
                        identidad = {
                            'empleado_id': fila['empleado_id'],
                            'fecha': date.fromisoformat(fila['fecha']),
                        }
                        reemplazar = request.POST.get(f'reemplazar_{indice}') == 'on'
                        try:
                            with transaction.atomic():
                                horario = HorarioDiario.objects.filter(
                                    **identidad
                                ).first()
                                if horario and not reemplazar:
                                    omitidos += 1
                                    continue
                                es_nuevo = horario is None
                                if es_nuevo:
                                    horario = HorarioDiario(**identidad)
                                    horario.creado_por = request.user
                                horario.hora_entrada = (
                                    fila['hora_entrada'] or None
                                )
                                horario.hora_salida = fila['hora_salida'] or None
                                horario.es_franco = fila['es_franco']
                                horario.observaciones = fila['observaciones']
                                horario.full_clean()
                                horario.save()
                                cambiar_predeterminado = (
                                    fila.get('predeterminado_inicial', False)
                                    or request.POST.get(
                                        f'predeterminado_{fila["indice"]}',
                                    ) == 'on'
                                )
                                if cambiar_predeterminado and horario.es_franco:
                                    raise ValidationError(
                                        'Un día franco no puede convertirse '
                                        'en horario predeterminado.'
                                    )
                                if cambiar_predeterminado:
                                    establecer_horario_predeterminado(
                                        horario.empleado,
                                        horario.fecha,
                                        horario.hora_entrada,
                                        horario.hora_salida,
                                        horario.observaciones,
                                        request.user,
                                    )
                                    predeterminados_actualizados += 1
                                if es_nuevo:
                                    creados += 1
                                else:
                                    reemplazados += 1
                        except (ValidationError, IntegrityError) as exc:
                            errores_carga.append(
                                f"Fila {fila['fila']}: "
                                + (
                                    '; '.join(exc.messages)
                                    if isinstance(exc, ValidationError)
                                    else 'conflicto al guardar el horario'
                                )
                            )
                request.session.pop('horarios_laborales_preview', None)
                if errores_carga:
                    messages.warning(
                        request,
                        f'Carga parcial: {creados} creados, {reemplazados} '
                        f'reemplazados, {omitidos} omitidos y '
                        f'{predeterminados_actualizados} predeterminado(s) '
                        'actualizado(s). Revisa los errores.',
                    )
                else:
                    messages.success(
                        request,
                        f'Carga finalizada: {creados} creados, {reemplazados} '
                        f'reemplazados, {omitidos} omitidos y '
                        f'{predeterminados_actualizados} predeterminado(s) '
                        'actualizado(s).',
                    )
                if errores_carga:
                    request.session['horarios_laborales_errores'] = errores_carga
                return redirect('web:horarios_laborales')
        else:
            errores_carga.append('La acción solicitada no es válida.')

    carga_pendiente = request.session.pop('horarios_laborales_preview', None)
    if carga_pendiente:
        filas_previsualizadas = carga_pendiente['filas']
        pares = []
        for inicio in range(0, len(filas_previsualizadas), 100):
            grupo = filas_previsualizadas[inicio:inicio + 100]
            condicion = Q(pk__in=[])
            for fila in grupo:
                condicion |= Q(
                    empleado_id=fila['empleado_id'],
                    fecha=date.fromisoformat(fila['fecha']),
                )
            existentes = {
                (horario.empleado_id, horario.fecha)
                for horario in HorarioDiario.objects.filter(condicion)
            }
            pares.extend(existentes)
        pares = set(pares)
        for indice, fila in enumerate(filas_previsualizadas):
            fila['indice'] = indice
            fila.setdefault('predeterminado_inicial', False)
            fila['duplicado'] = (
                fila['empleado_id'],
                date.fromisoformat(fila['fecha']),
            ) in pares
        request.session['horarios_laborales_preview'] = carga_pendiente
        errores_carga.extend(carga_pendiente.get('errores', []))
    errores_carga.extend(
        request.session.pop('horarios_laborales_errores', [])
    )

    errores.extend(errores_carga)
    fechas = {}
    for parametro in ('fecha_desde', 'fecha_hasta'):
        valor = request.GET.get(parametro, '')
        fechas[parametro] = valor
        if valor:
            try:
                fechas[parametro] = date.fromisoformat(valor)
            except ValueError:
                errores.append(f'{parametro}: usa el formato AAAA-MM-DD.')

    if not errores:
        if fechas['fecha_desde']:
            horarios = horarios.filter(fecha__gte=fechas['fecha_desde'])
        if fechas['fecha_hasta']:
            horarios = horarios.filter(fecha__lte=fechas['fecha_hasta'])
        if (
            fechas['fecha_desde']
            and fechas['fecha_hasta']
            and fechas['fecha_hasta'] < fechas['fecha_desde']
        ):
            errores.append('La fecha hasta no puede ser anterior a la fecha desde.')

    paginator = Paginator(horarios if not errores else HorarioDiario.objects.none(), 20)
    pagina = paginator.get_page(request.GET.get('page'))
    horarios_pagina = list(pagina.object_list)
    condiciones_predeterminadas = Q(pk__in=[])
    for horario in horarios_pagina:
        condiciones_predeterminadas |= Q(
            empleado_id=horario.empleado_id,
            vigente_desde=horario.fecha,
        )
    predeterminados_de_pagina = set(
        HorarioPredeterminado.objects.filter(
            condiciones_predeterminadas,
        ).values_list('empleado_id', 'vigente_desde')
    )
    for horario in horarios_pagina:
        horario.es_predeterminado = (
            horario.empleado_id,
            horario.fecha,
        ) in predeterminados_de_pagina
    return render(request, 'web/horarios_laborales.html', {
        'horarios': pagina,
        'fecha_desde': request.GET.get('fecha_desde', ''),
        'fecha_hasta': request.GET.get('fecha_hasta', ''),
        'errores': errores,
        'puede_ver_todos': rol in roles_con_acceso_general,
        'puede_gestionar': puede_gestionar,
        'formulario_horario': formulario,
        'filas_previsualizadas': filas_previsualizadas,
        'token_previsualizacion': (
            carga_pendiente.get('token') if carga_pendiente else ''
        ),
    })


@login_required
def plantilla_horarios_laborales(request):
    if rol_de(request.user) not in ('GERENTE', 'ADMINISTRATIVO'):
        raise PermissionDenied('Solo GERENTE o ADMINISTRATIVO puede descargar la plantilla.')
    respuesta = HttpResponse(
        'legajo,fecha,hora_entrada,hora_salida,es_franco,observaciones\r\n'
        'EMP-001,2026-10-21,09:00,18:00,No,Turno habitual\r\n'
        'EMP-001,2026-10-22,,,Sí,Franco semanal\r\n',
        content_type='text/csv; charset=utf-8',
    )
    respuesta['Content-Disposition'] = (
        'attachment; filename="plantilla_horarios.csv"'
    )
    return respuesta


@login_required
def dashboard(request):
    hoy = timezone.localdate()
    kpis = [
        {'titulo': 'Empleados activos', 'valor': Empleado.objects.filter(estado='ACTIVO').count(),
         'icono': 'bi-people', 'color': 'primary'},
        {'titulo': 'Total de empleados', 'valor': Empleado.objects.count(),
         'icono': 'bi-person-lines-fill', 'color': 'secondary'},
        {'titulo': 'Puestos activos', 'valor': Puesto.objects.filter(activo=True).count(),
         'icono': 'bi-briefcase', 'color': 'info'},
        {'titulo': 'Incidencias abiertas',
         'valor': Incidencia.objects.exclude(estado__in=['RESUELTA', 'CERRADA']).count(),
         'icono': 'bi-inbox', 'color': 'warning'},
        {'titulo': 'Sanciones', 'valor': Sancion.objects.count(),
         'icono': 'bi-exclamation-triangle', 'color': 'danger'},
        {'titulo': 'Licencias pendientes',
         'valor': SolicitudLicencia.objects.filter(estado='PENDIENTE').count(),
         'icono': 'bi-calendar-check', 'color': 'success'},
    ]
    por_unidad = [
        {'etiqueta': x['unidad__nombre'] or 'Sin asignar', 'total': x['total']}
        for x in Empleado.objects.filter(estado='ACTIVO')
        .values('unidad__nombre').annotate(total=Count('id')).order_by('-total')
    ]
    inc_estado = [
        {'etiqueta': x['estado'], 'total': x['total']}
        for x in Incidencia.objects.values('estado').annotate(total=Count('id'))
    ]
    return render(request, 'web/dashboard.html', {
        'kpis': kpis, 'por_unidad': por_unidad, 'inc_estado': inc_estado,
    })


@login_required
def mis_licencias(request):
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if empleado is None:
        raise PermissionDenied('El usuario no tiene un legajo de empleado vinculado.')

    form = LicenciaAutogestionForm(
        request.POST or None,
        empleado=empleado,
    )
    if request.method == 'POST' and form.is_valid():
        SolicitudLicencia.objects.create(
            empleado=empleado,
            tipo_licencia=form.cleaned_data['tipo_licencia'],
            fecha_inicio=form.cleaned_data['fecha_inicio'],
            fecha_fin=form.cleaned_data['fecha_fin'],
            dias_solicitados=form.cleaned_data['dias_solicitados'],
            motivo=form.cleaned_data['motivo'],
            solicitado_por=request.user,
        )
        messages.success(request, 'La solicitud de licencia se envió para revisión.')
        return redirect('web:mis_licencias')

    anio = timezone.localdate().year
    saldo_actual = SaldoVacaciones.objects.filter(
        empleado=empleado, anio=anio,
    ).first()
    dias_disponibles = (
        saldo_actual.dias_pendientes
        if saldo_actual
        else dias_vacaciones_por_antiguedad(empleado, anio)
    )
    solicitudes = SolicitudLicencia.objects.filter(
        empleado=empleado,
    ).select_related('tipo_licencia').order_by('-fecha_solicitud')
    return render(request, 'web/mis_licencias.html', {
        'form': form,
        'solicitudes': solicitudes,
        'anio': anio,
        'dias_disponibles': dias_disponibles,
    })


@login_required
def cancelar_mi_licencia(request, pk):
    if request.method != 'POST':
        raise PermissionDenied('La cancelación debe enviarse mediante POST.')
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if empleado is None:
        raise PermissionDenied('El usuario no tiene un legajo de empleado vinculado.')
    solicitud = get_object_or_404(SolicitudLicencia, pk=pk, empleado=empleado)
    try:
        cancelar_solicitud(solicitud.pk, request.user, 'Cancelada por el empleado.')
    except ValidationError as exc:
        errors = (
            [error for field_errors in exc.message_dict.values() for error in field_errors]
            if hasattr(exc, 'message_dict') else exc.messages
        )
        messages.error(request, ' '.join(str(error) for error in errors))
    else:
        messages.success(request, 'La solicitud se canceló correctamente.')
    return redirect('web:mis_licencias')


@login_required
def modulo_list(request, slug):
    cfg = MODULOS.get(slug)
    if cfg is None:
        messages.error(request, 'Módulo no encontrado.')
        return redirect('web:dashboard')
    if _es_reclutamiento(slug) and not _puede_ver_reclutamiento(request.user):
        messages.error(request, 'No tenés permiso para consultar este módulo.')
        return redirect('web:dashboard')

    modelo = cfg['model']
    form_class = cfg['form']
    qs = modelo.objects.all()
    fecha_filtro = None
    if slug == 'asistencia':
        fecha_texto = request.GET.get('fecha', '').strip()
        try:
            fecha_filtro = date.fromisoformat(fecha_texto) if fecha_texto else timezone.localdate()
        except ValueError:
            messages.error(request, 'La fecha debe tener formato YYYY-MM-DD.')
            fecha_filtro = timezone.localdate()
        qs = qs.filter(fecha=fecha_filtro).select_related('empleado').order_by(
            'empleado__apellido',
            'empleado__nombre',
            'empleado__legajo',
        )

    q = request.GET.get('q', '').strip()
    if q and cfg.get('search'):
        condicion = None
        from django.db.models import Q
        for campo in cfg['search']:
            c = Q(**{f'{campo}__icontains': q})
            condicion = c if condicion is None else condicion | c
        qs = qs.filter(condicion)

    puede_operar = _puede_operar(request.user)
    editable = form_class is not None

    form = None
    if editable and puede_operar:
        if request.method == 'POST':
            form = form_class(request.POST, request.FILES)
            if form.is_valid():
                if slug == 'licencias':
                    solicitud = form.save(commit=False)
                    solicitud.solicitado_por = request.user
                    solicitud.save()
                elif slug == 'sanciones':
                    sancion = form.save(commit=False)
                    sancion.responsable = request.user
                    sancion.save()
                else:
                    form.save()
                messages.success(request, f'{cfg["titulo"]}: registro creado correctamente.')
                return redirect('web:modulo', slug=slug)
        else:
            form = form_class()

    filas = []
    if slug == 'asistencia':
        empleados = Empleado.objects.filter(estado=Empleado.Estado.ACTIVO)
        if q:
            from django.db.models import Q
            empleados = empleados.filter(
                Q(legajo__icontains=q)
                | Q(apellido__icontains=q)
                | Q(nombre__icontains=q)
            )
        empleados = empleados.order_by('apellido', 'nombre', 'legajo')
        empleados_ids = list(empleados.values_list('pk', flat=True))
        registros = {
            registro.empleado_id: registro
            for registro in RegistroAsistencia.objects.filter(
                empleado_id__in=empleados_ids,
                fecha=fecha_filtro,
            ).select_related('empleado')
        }
        solicitudes_en_rango = SolicitudLicencia.objects.filter(
            empleado_id__in=empleados_ids,
            fecha_inicio__lte=fecha_filtro,
            fecha_fin__gte=fecha_filtro,
        ).values_list('empleado_id', 'tipo_licencia__descuenta_vacaciones')
        vacaciones = set()
        licencias = set()
        for empleado_id, descuenta_vacaciones in solicitudes_en_rango:
            (vacaciones if descuenta_vacaciones else licencias).add(empleado_id)
        feriado = Feriado.objects.filter(fecha=fecha_filtro).exists()

        for empleado in empleados:
            registro = registros.get(empleado.pk)
            tiene_licencia = empleado.pk in licencias
            tiene_vacaciones_laborable = (
                empleado.pk in vacaciones
                and fecha_filtro.weekday() < 5
                and not feriado
            )
            if (
                registro is not None
                and registro.tipo == RegistroAsistencia.Tipo.AUSENTE
                and (tiene_vacaciones_laborable or tiene_licencia)
            ):
                valores = [display(registro, attr) for _, attr in cfg['columnas']]
                valores[2] = (
                    RegistroAsistencia.Tipo.VACACIONES.label
                    if tiene_vacaciones_laborable
                    else RegistroAsistencia.Tipo.LICENCIA.label
                )
                fila_id = None
                automatico = True
            elif registro is not None:
                valores = [display(registro, attr) for _, attr in cfg['columnas']]
                fila_id = registro.pk
                automatico = False
            else:
                if tiene_vacaciones_laborable:
                    tipo = RegistroAsistencia.Tipo.VACACIONES.label
                elif tiene_licencia:
                    tipo = RegistroAsistencia.Tipo.LICENCIA.label
                elif fecha_filtro.weekday() < 5 and not feriado:
                    tipo = RegistroAsistencia.Tipo.AUSENTE.label
                elif feriado:
                    tipo = RegistroAsistencia.Tipo.FERIADO.label
                else:
                    tipo = 'No laborable'
                valores = [
                    str(empleado),
                    fecha_filtro,
                    tipo,
                    '',
                    '',
                    '',
                ]
                fila_id = None
                automatico = True
            filas.append({
                'id': fila_id,
                'empleado_id': empleado.pk,
                'valores': valores,
                'puede_editar': False,
                'puede_cancelar': False,
                'automatico': automatico,
            })
        total = len(filas)
    else:
        for obj in qs[:300]:
            puede_editar_solicitud = not isinstance(obj, SolicitudLicencia) or obj.estado in (
                SolicitudLicencia.Estado.PENDIENTE,
                SolicitudLicencia.Estado.BORRADOR,
            )
            puede_cancelar_solicitud = isinstance(obj, SolicitudLicencia) and obj.estado in (
                SolicitudLicencia.Estado.PENDIENTE,
                SolicitudLicencia.Estado.APROBADA,
            )
            filas.append({
                'id': obj.pk,
                'valores': [display(obj, attr) for _, attr in cfg['columnas']],
                'puede_editar': puede_editar_solicitud,
                'puede_cancelar': puede_cancelar_solicitud,
                'automatico': False,
            })
        total = qs.count()
    num_columnas = len(cfg['columnas']) + (1 if (editable and puede_operar) else 0)
    return render(request, 'web/lista.html', {
        'cfg': cfg, 'slug': slug, 'filas': filas, 'columnas': cfg['columnas'],
        'form': form, 'q': q, 'total': total,
        'editable': editable, 'puede_operar': puede_operar, 'num_columnas': num_columnas,
        'fecha_filtro': fecha_filtro,
    })


@login_required
def asistencia_empleado_mes(request, empleado_id):
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    hoy = timezone.localdate()
    mes_texto = request.GET.get('mes', '')
    try:
        anio, mes = (
            (int(mes_texto[:4]), int(mes_texto[5:7]))
            if len(mes_texto) == 7 and mes_texto[4] == '-'
            else (hoy.year, hoy.month)
        )
        inicio_mes = date(anio, mes, 1)
    except (TypeError, ValueError):
        messages.error(request, 'Selecciona un mes válido.')
        inicio_mes = date(hoy.year, hoy.month, 1)
    if inicio_mes.month == 12:
        fin_mes = date(inicio_mes.year + 1, 1, 1)
    else:
        fin_mes = date(inicio_mes.year, inicio_mes.month + 1, 1)
    fin_inclusivo = fin_mes - timedelta(days=1)

    registros = list(
        RegistroAsistencia.objects.filter(
            empleado=empleado,
            fecha__gte=inicio_mes,
            fecha__lt=fin_mes,
        ).order_by('fecha')
    )
    for registro in registros:
        registro.horario_esperado = obtener_horario_esperado(
            empleado,
            registro.fecha,
        )
    licencias = list(
        SolicitudLicencia.objects.filter(
            empleado=empleado,
            fecha_inicio__lt=fin_mes,
            fecha_fin__gte=inicio_mes,
        ).select_related('tipo_licencia').order_by('fecha_inicio')
    )
    incidencias = list(
        Incidencia.objects.filter(
            empleado=empleado,
            fecha_creacion__year=inicio_mes.year,
            fecha_creacion__month=inicio_mes.month,
        ).order_by('-fecha_creacion')
    )
    alertas_asistencia = [
        registro for registro in registros
        if registro.tipo in (
            RegistroAsistencia.Tipo.AUSENTE,
            RegistroAsistencia.Tipo.TARDANZA,
            RegistroAsistencia.Tipo.RETIRO_ANTICIPADO,
        )
        or registro.observaciones
    ]
    resumen = {
        'asistencias': sum(
            registro.tipo in (
                RegistroAsistencia.Tipo.PRESENTE,
                RegistroAsistencia.Tipo.TARDANZA,
                RegistroAsistencia.Tipo.RETIRO_ANTICIPADO,
            )
            for registro in registros
        ),
        'ausencias': sum(
            registro.tipo == RegistroAsistencia.Tipo.AUSENTE
            for registro in registros
        ),
        'horas_extra_minutos': sum(registro.minutos_extra for registro in registros),
        'vacaciones': sum(
            (
                solicitud.dias_solicitados
                for solicitud in licencias
                if solicitud.tipo_licencia.descuenta_vacaciones
            ),
            Decimal('0'),
        ),
        'licencias': sum(
            (
                solicitud.dias_solicitados
                for solicitud in licencias
                if not solicitud.tipo_licencia.descuenta_vacaciones
            ),
            Decimal('0'),
        ),
        'tardanzas': sum(
            registro.tipo == RegistroAsistencia.Tipo.TARDANZA
            for registro in registros
        ),
    }
    resumen['horas_extra_horas'], resumen['horas_extra_resto'] = divmod(
        resumen['horas_extra_minutos'],
        60,
    )
    return render(request, 'web/asistencia_empleado_mes.html', {
        'empleado': empleado,
        'mes': inicio_mes.strftime('%Y-%m'),
        'mes_nombre': inicio_mes.strftime('%B %Y'),
        'inicio_mes': inicio_mes,
        'fin_mes': fin_inclusivo,
        'resumen': resumen,
        'registros': registros,
        'licencias': licencias,
        'incidencias': incidencias,
        'alertas_asistencia': alertas_asistencia,
    })


@login_required
def incidencia_detalle(request, pk):
    incidencia = get_object_or_404(Incidencia, pk=pk)
    if request.method == 'POST':
        texto = request.POST.get('comentario', '').strip()
        if texto:
            ComentarioIncidencia.objects.create(
                incidencia=incidencia, usuario=request.user, comentario=texto,
            )
            messages.success(request, 'Comentario agregado.')
            return redirect('web:incidencia_detalle', pk=pk)
    return render(request, 'web/incidencia_detalle.html', {'incidencia': incidencia})


@login_required
def reportes_view(request):
    reportes = [
        {'slug': 'resumen', 'titulo': 'Resumen general (KPIs)', 'icono': 'bi-speedometer2'},
        {'slug': 'nomina', 'titulo': 'Nómina de personal activo', 'icono': 'bi-people'},
        {'slug': 'cargos-vacantes', 'titulo': 'Cargos ocupados y vacantes', 'icono': 'bi-briefcase'},
        {'slug': 'ausentismo', 'titulo': 'Ausentismo', 'icono': 'bi-clock-history'},
        {'slug': 'vacaciones-pendientes', 'titulo': 'Vacaciones pendientes', 'icono': 'bi-calendar-check'},
        {'slug': 'documentacion-vencida', 'titulo': 'Documentación vencida', 'icono': 'bi-file-earmark-x'},
        {'slug': 'incidencias', 'titulo': 'Incidencias', 'icono': 'bi-inbox'},
        {'slug': 'sanciones', 'titulo': 'Sanciones', 'icono': 'bi-exclamation-triangle'},
        {'slug': 'promociones-potenciales', 'titulo': 'Promociones potenciales', 'icono': 'bi-graph-up-arrow'},
    ]
    return render(request, 'web/reportes.html', {'reportes': reportes})


# ---------------------------------------------------------------------------
# Gestión de usuarios y roles (solo Gerente de RRHH)
# ---------------------------------------------------------------------------
def _es_gerente(user):
    from apps.accounts.permissions import rol_de
    return rol_de(user) == 'GERENTE'


def _puede_operar(user):
    from apps.accounts.permissions import rol_de
    return rol_de(user) in ('GERENTE', 'ADMINISTRATIVO')


def _es_reclutamiento(slug):
    return slug in (
        'vacantes', 'postulantes', 'postulaciones', 'entrevistas',
    )


def _puede_ver_reclutamiento(user):
    from apps.accounts.permissions import rol_de
    return rol_de(user) in ('GERENTE', 'ADMINISTRATIVO')


def _aplicar_rol(user, rol):
    from django.contrib.auth.models import Group

    from apps.accounts.models import PerfilUsuario
    from apps.accounts.serializers import MAPA_ROL_GRUPO

    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
    perfil.rol = rol
    perfil.save(update_fields=['rol'])
    user.groups.clear()
    nombre = MAPA_ROL_GRUPO.get(rol)
    if nombre:
        grupo, _ = Group.objects.get_or_create(name=nombre)
        user.groups.add(grupo)


@login_required
def usuarios_listar(request):
    if not _es_gerente(request.user):
        messages.error(request, 'No tenés permiso para administrar usuarios.')
        return redirect('web:dashboard')
    usuarios = User.objects.all().prefetch_related('groups').order_by('username')
    return render(request, 'web/usuarios.html', {'usuarios': usuarios, 'form': UsuarioForm()})


@login_required
def usuario_crear(request):
    if not _es_gerente(request.user):
        messages.error(request, 'No tenés permiso para administrar usuarios.')
        return redirect('web:dashboard')
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if not form.cleaned_data.get('password'):
                form.add_error('password', 'La contraseña es obligatoria al crear un usuario.')
            else:
                user.set_password(form.cleaned_data['password'])
                user.save()
                _aplicar_rol(user, form.cleaned_data['rol'])
                messages.success(request, f'Usuario "{user.username}" creado correctamente.')
                return redirect('web:usuarios')
    else:
        form = UsuarioForm()
    usuarios = User.objects.all().prefetch_related('groups').order_by('username')
    return render(request, 'web/usuarios.html', {
        'usuarios': usuarios, 'form': form, 'abrir_modal': True,
    })


@login_required
def usuario_editar(request, pk):
    if not _es_gerente(request.user):
        messages.error(request, 'No tenés permiso para administrar usuarios.')
        return redirect('web:dashboard')
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            user = form.save(commit=False)
            if form.cleaned_data.get('password'):
                user.set_password(form.cleaned_data['password'])
            user.save()
            _aplicar_rol(user, form.cleaned_data['rol'])
            messages.success(request, f'Usuario "{user.username}" actualizado.')
            return redirect('web:usuarios')
    else:
        rol_actual = getattr(getattr(usuario, 'perfil', None), 'rol', 'ADMINISTRATIVO')
        form = UsuarioForm(instance=usuario, initial={'rol': rol_actual})
    return render(request, 'web/usuario_form.html', {'form': form, 'usuario': usuario})


@login_required
def usuario_eliminar(request, pk):
    if not _es_gerente(request.user):
        messages.error(request, 'No tenés permiso para administrar usuarios.')
        return redirect('web:dashboard')
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if usuario == request.user:
            messages.error(request, 'No podés eliminar tu propio usuario.')
        elif usuario.is_superuser:
            messages.error(request, 'No se puede eliminar un superusuario.')
        else:
            nombre = usuario.username
            usuario.delete()
            messages.success(request, f'Usuario "{nombre}" eliminado.')
    return redirect('web:usuarios')


@login_required
def modulo_editar(request, slug, pk):
    cfg = MODULOS.get(slug)
    if cfg is None or cfg['form'] is None:
        messages.error(request, 'Módulo no editable.')
        return redirect('web:dashboard')
    if _es_reclutamiento(slug) and not _puede_ver_reclutamiento(request.user):
        messages.error(request, 'No tenés permiso para consultar este módulo.')
        return redirect('web:dashboard')
    if not _puede_operar(request.user):
        messages.error(request, 'No tenés permiso para editar este módulo.')
        return redirect('web:modulo', slug=slug)
    objeto = get_object_or_404(cfg['model'], pk=pk)
    if isinstance(objeto, Sancion) and objeto.estado != Sancion.Estado.PROPUESTA:
        messages.error(request, 'Solo se pueden editar sanciones en estado de propuesta.')
        return redirect('web:modulo', slug=slug)
    if request.method == 'POST':
        form = cfg['form'](request.POST, request.FILES, instance=objeto)
        if form.is_valid():
            form.save()
            messages.success(request, f'{cfg["titulo"]}: registro actualizado correctamente.')
            return redirect('web:modulo', slug=slug)
    else:
        form = cfg['form'](instance=objeto)
    return render(request, 'web/modulo_editar.html', {
        'cfg': cfg, 'slug': slug, 'form': form, 'objeto': objeto,
    })


@login_required
def modulo_eliminar(request, slug, pk):
    cfg = MODULOS.get(slug)
    if cfg is None:
        messages.error(request, 'Módulo no encontrado.')
        return redirect('web:dashboard')
    if _es_reclutamiento(slug) and not _puede_ver_reclutamiento(request.user):
        messages.error(request, 'No tenés permiso para consultar este módulo.')
        return redirect('web:dashboard')
    if not _puede_operar(request.user):
        messages.error(request, 'No tenés permiso para eliminar en este módulo.')
        return redirect('web:modulo', slug=slug)
    if _es_reclutamiento(slug) and not _es_gerente(request.user):
        messages.error(request, 'Solo el Gerente puede eliminar registros de Reclutamiento.')
        return redirect('web:modulo', slug=slug)
    objeto = get_object_or_404(cfg['model'], pk=pk)
    if request.method == 'POST':
        if isinstance(objeto, SolicitudLicencia):
            try:
                cancelar_solicitud(objeto.pk, request.user, 'Cancelada desde el módulo de licencias.')
            except ValidationError as exc:
                errors = (
                    [error for field_errors in exc.message_dict.values() for error in field_errors]
                    if hasattr(exc, 'message_dict') else exc.messages
                )
                messages.error(request, ' '.join(str(error) for error in errors))
            else:
                messages.success(request, 'La solicitud de licencia se canceló correctamente.')
            return redirect('web:modulo', slug=slug)
        try:
            objeto.delete()
            messages.success(request, f'{cfg["titulo"]}: registro eliminado.')
        except Exception as exc:  # modelos protegidos (historial, etc.)
            messages.error(
                request,
                f'No se puede eliminar este registro porque tiene datos relacionados ({exc}).',
            )
    return redirect('web:modulo', slug=slug)
