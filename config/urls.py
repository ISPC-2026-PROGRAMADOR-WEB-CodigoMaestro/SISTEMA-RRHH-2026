"""
URL configuration – Sistema de Gestión de Recursos Humanos.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Dashboard web (interfaz de usuario)
    path('asistencia/', include('apps.asistencia.web_urls')),
    path('', include('apps.web.urls')),

    # Auth JWT
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Documentación OpenAPI / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # ------------------------------------------------------------------
    # API por modulo
    # ------------------------------------------------------------------
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/auditoria/', include('apps.auditoria.urls')),
    path('api/organizacion/', include('apps.organizacion.urls')),
    path('api/puestos/', include('apps.puestos.urls')),
    path('api/empleados/', include('apps.empleados.urls')),
    path('api/asistencia/', include('apps.asistencia.urls')),
    path('api/licencias/', include('apps.licencias.urls')),
    path('api/evaluaciones/', include('apps.evaluaciones.urls')),
    path('api/sanciones/', include('apps.sanciones.urls')),
    path('api/incidencias/', include('apps.incidencias.urls')),
    path('api/capacitaciones/', include('apps.capacitaciones.urls')),
    path('api/reportes/', include('apps.reportes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = 'Gestión de Recursos Humanos'
admin.site.site_title = 'RRHH Admin'
admin.site.index_title = 'Panel de administración'
