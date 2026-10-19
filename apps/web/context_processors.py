"""Context processor para el menú lateral del dashboard."""
from .registro import MODULOS

ORDEN_MENU = [
    'empleados', 'unidades', 'puestos', 'designaciones', 'documentos',
    'asistencia', 'licencias', 'evaluaciones', 'sanciones', 'incidencias',
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
    return {
        'menu_items': items,
        'es_gerente': rol_de(getattr(request, 'user', None)) == 'GERENTE',
    }
