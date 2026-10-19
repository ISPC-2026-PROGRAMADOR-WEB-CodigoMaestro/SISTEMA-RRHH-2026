"""Vistas del dashboard web (Django templates + Bootstrap)."""
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.empleados.models import Empleado
from apps.incidencias.models import ComentarioIncidencia, Incidencia
from apps.licencias.models import SolicitudLicencia
from apps.puestos.models import Puesto
from apps.sanciones.models import Sancion

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
def modulo_list(request, slug):
    cfg = MODULOS.get(slug)
    if cfg is None:
        messages.error(request, 'Módulo no encontrado.')
        return redirect('web:dashboard')

    modelo = cfg['model']
    form_class = cfg['form']
    qs = modelo.objects.all()

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
                form.save()
                messages.success(request, f'{cfg["titulo"]}: registro creado correctamente.')
                return redirect('web:modulo', slug=slug)
        else:
            form = form_class()

    filas = [
        {'id': obj.pk, 'valores': [display(obj, attr) for _, attr in cfg['columnas']]}
        for obj in qs[:300]
    ]
    num_columnas = len(cfg['columnas']) + (1 if (editable and puede_operar) else 0)
    return render(request, 'web/lista.html', {
        'cfg': cfg, 'slug': slug, 'filas': filas, 'columnas': cfg['columnas'],
        'form': form, 'q': q, 'total': qs.count(),
        'editable': editable, 'puede_operar': puede_operar, 'num_columnas': num_columnas,
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
    if not _puede_operar(request.user):
        messages.error(request, 'No tenés permiso para editar este módulo.')
        return redirect('web:modulo', slug=slug)
    objeto = get_object_or_404(cfg['model'], pk=pk)
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
    if not _puede_operar(request.user):
        messages.error(request, 'No tenés permiso para eliminar en este módulo.')
        return redirect('web:modulo', slug=slug)
    objeto = get_object_or_404(cfg['model'], pk=pk)
    if request.method == 'POST':
        try:
            objeto.delete()
            messages.success(request, f'{cfg["titulo"]}: registro eliminado.')
        except Exception as exc:  # modelos protegidos (historial, etc.)
            messages.error(
                request,
                f'No se puede eliminar este registro porque tiene datos relacionados ({exc}).',
            )
    return redirect('web:modulo', slug=slug)

