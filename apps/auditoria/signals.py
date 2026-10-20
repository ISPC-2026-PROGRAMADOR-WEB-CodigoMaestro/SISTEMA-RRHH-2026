"""Señales que registran automáticamente cambios en la bitácora de auditoría."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .middleware import get_current_request
from .models import RegistroAuditoria

# Modelos de los que se guarda trazabilidad automática.
MODELOS_AUDITADOS = {
    'accounts.PerfilUsuario',
    'empleados.Empleado',
    'empleados.DocumentoLegajo',
    'empleados.HistorialLaboral',
    'organizacion.UnidadOrganizacional',
    'puestos.Puesto',
    'puestos.Designacion',
    'asistencia.RegistroAsistencia',
    'licencias.SolicitudLicencia',
    'sanciones.Sancion',
    'incidencias.Incidencia',
}


def _contexto():
    request = get_current_request()
    usuario = ip = None
    ruta = ua = ''
    if request is not None:
        u = getattr(request, 'user', None)
        if u is not None and getattr(u, 'is_authenticated', False):
            usuario = u
        ip = request.META.get('REMOTE_ADDR')
        ruta = request.path[:300]
        ua = request.META.get('HTTP_USER_AGENT', '')[:300]
    return usuario, ip, ruta, ua


def _descripcion(instance):
    try:
        return str(instance)[:500]
    except Exception:
        return instance._meta.label


def _crear_registro(accion, instance):
    usuario, ip, ruta, ua = _contexto()
    try:
        RegistroAuditoria.objects.create(
            usuario=usuario,
            accion=accion,
            modelo=instance._meta.label,
            objeto_id=str(getattr(instance, 'pk', '')),
            descripcion=_descripcion(instance),
            ip=ip,
            ruta=ruta,
            user_agent=ua,
        )
    except Exception:
        # Nunca interrumpir la operación principal por un fallo de auditoría.
        pass


@receiver(post_save)
def _auditar_save(sender, instance, created, **kwargs):
    if sender._meta.label not in MODELOS_AUDITADOS:
        return
    _crear_registro('CREATE' if created else 'UPDATE', instance)


@receiver(post_delete)
def _auditar_delete(sender, instance, **kwargs):
    if sender._meta.label not in MODELOS_AUDITADOS:
        return
    _crear_registro('DELETE', instance)
