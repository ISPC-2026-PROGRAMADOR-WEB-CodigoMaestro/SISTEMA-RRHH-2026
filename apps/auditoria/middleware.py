"""Middleware que expone el request/usuario actual para la auditoría."""
import threading

_local = threading.local()


def get_current_request():
    return getattr(_local, 'request', None)


def get_current_user():
    request = get_current_request()
    if request is None:
        return None
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return user
    return None


class AuditoriaMiddleware:
    """Almacena el request en un objeto local al hilo durante su procesamiento."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            response = self.get_response(request)
        finally:
            _local.request = None
        return response
