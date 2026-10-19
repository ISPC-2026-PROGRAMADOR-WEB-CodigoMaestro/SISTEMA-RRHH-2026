"""Rutas de la app accounts."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CambiarPasswordView,
    GrupoViewSet,
    PerfilActualView,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register('usuarios', UsuarioViewSet, basename='usuario')
router.register('grupos', GrupoViewSet, basename='grupo')

urlpatterns = [
    path('me/', PerfilActualView.as_view(), name='perfil-actual'),
    path('cambiar-password/', CambiarPasswordView.as_view(), name='cambiar-password'),
    path('', include(router.urls)),
]
