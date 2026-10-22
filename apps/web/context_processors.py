"""Context processor para el menú lateral del dashboard."""
from .registro import MODULOS

ORDEN_MENU = [
    'empleados', 'unidades', 'puestos', 'designaciones', 'documentos',
    'asistencia', 'licencias', 'evaluaciones', 'capacitaciones', 'sanciones', 'incidencias',
    'historial',
]


def menu(request):
    items = []
    for slug in ORDEN_MENU:
        modulo = MODULOS.get(slug)
        if modulo:
            items.append({
                'slug': slug,
                'titulo': modulo['titulo'],
                'icono': modulo['icono'],
            })
    from apps.accounts.permissions import rol_de
    user = getattr(request, 'user', None)
    from apps.empleados.models import Empleado
    tiene_legajo = (
        user.is_authenticated
        and Empleado.objects.filter(usuario_id=user.pk).exists()
    )
    return {
        'menu_items': items,
        'es_gerente': rol_de(user) == 'GERENTE',
        'tiene_legajo': tiene_legajo,
        'puede_operar_personal': rol_de(user) in ('GERENTE', 'ADMINISTRATIVO'),
        'puede_ver_horarios': (
            user.is_authenticated
            and (
                rol_de(user) in ('GERENTE', 'ADMINISTRATIVO', 'LECTURA')
                or tiene_legajo
            )
        ),
    }
