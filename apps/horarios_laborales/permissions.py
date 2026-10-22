from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.permissions import OperarPersonal


class GestionarHorariosOPropioEmpleado(BasePermission):
    message = 'No tiene permisos para realizar esta operación.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return OperarPersonal().has_permission(request, view)
