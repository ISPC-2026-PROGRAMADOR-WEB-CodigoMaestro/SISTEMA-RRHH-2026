from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.permissions import OperarPersonal, rol_de


class VerAsistenciaPropiaOOperarPersonal(BasePermission):
    message = 'No tiene permisos para realizar esta operación.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if rol_de(request.user) in ('GERENTE', 'ADMINISTRATIVO', 'LECTURA'):
            return OperarPersonal().has_permission(request, view)
        if request.method in SAFE_METHODS:
            try:
                return request.user.empleado is not None
            except AttributeError:
                return False
        return OperarPersonal().has_permission(request, view)
