"""Bitacora de auditoria y trazabilidad."""
from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):
    class Accion(models.TextChoices):
        CREATE = 'CREATE', 'Creacion'
        UPDATE = 'UPDATE', 'Modificacion'
        DELETE = 'DELETE', 'Eliminacion'
        LOGIN = 'LOGIN', 'Inicio de sesion'
        LOGOUT = 'LOGOUT', 'Cierre de sesion'
        LOGIN_FAIL = 'LOGIN_FAIL', 'Fallo de autenticacion'
        APPROVE = 'APPROVE', 'Aprobacion'
        REJECT = 'REJECT', 'Rechazo'
        EXPORT = 'EXPORT', 'Exportacion'
        OTHER = 'OTHER', 'Otra'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_auditoria',
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    accion = models.CharField(max_length=15, choices=Accion.choices)
    modelo = models.CharField(max_length=100, blank=True, help_text='Ej: empleados.Empleado')
    objeto_id = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField(blank=True)
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    ruta = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = 'registro de auditoria'
        verbose_name_plural = 'registros de auditoria'
        ordering = ['-fecha_hora']

    def __str__(self):
        user = self.usuario or 'anonimo'
        return f'{self.fecha_hora} | {user} | {self.accion} | {self.modelo}'

    def delete(self, *args, **kwargs):
        raise models.ProtectedError(
            'Los registros de auditoria no pueden eliminarse.',
            self,
        )
