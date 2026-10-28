"""Vistas del dashboard web (Django templates + Bootstrap)."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.asistencia.models import Feriado, RegistroAsistencia
from apps.empleados.models import Empleado
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
