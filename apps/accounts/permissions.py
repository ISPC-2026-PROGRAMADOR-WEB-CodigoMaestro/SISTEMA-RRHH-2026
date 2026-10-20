"""Permisos y utilidades basadas en roles de Recursos Humanos."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


def rol_de(user):
    """Devuelve el rol efectivo del usuario ('GERENTE', 'ADMINISTRATIVO', ...)."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'GERENTE'
    perfil = getattr(user, 'perfil', None)
    if perfil is not None:
        return perfil.rol
    # Fallback: inferir por nombre de grupo
    for grupo in user.groups.all():
        nombre = grupo.name.lower()
        if 'gerente' in nombre:
            return 'GERENTE'
        if 'administrativo' in nombre:
            return 'ADMINISTRATIVO'
        if 'lectura' in nombre:
            return 'LECTURA'
    return None


class EsGerenteRRHH(BasePermission):
    """Solo Gerente General (o superusuario)."""

    message = 'Se requiere rol Gerente General.'

    def has_permission(self, request, view):
        return rol_de(request.user) == 'GERENTE'


class OperarPersonal(BasePermission):
    """
    Gerente: acceso total.
    Administrativo: lectura + alta/modificación (POST/PUT/PATCH), sin DELETE.
    Lectura: solo métodos seguros (GET/HEAD/OPTIONS).
    """

    message = 'No tiene permisos para realizar esta operación.'

    def has_permission(self, request, view):
        rol = rol_de(request.user)
        if rol == 'GERENTE':
            return True
        if request.method in SAFE_METHODS:
            return rol in ('ADMINISTRATIVO', 'LECTURA', 'GERENTE')
        if rol == 'ADMINISTRATIVO':
            return request.method in ('POST', 'PUT', 'PATCH')
        return False


class SoloLectura(BasePermission):
    """Permite únicamente métodos seguros."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
