"""Cuentas: perfil extendido y helpers de roles (Fase 2 ampliara esto)."""
from django.conf import settings
from django.db import models


class PerfilUsuario(models.Model):
    """Datos adicionales del usuario del sistema."""

    class RolPredeterminado(models.TextChoices):
        GERENTE = 'GERENTE', 'Gerente General'
        ADMINISTRATIVO = 'ADMINISTRATIVO', 'Administrativo de Recursos Humanos'
        SOLO_LECTURA = 'LECTURA', 'Solo lectura'
        PERSONALIZADO = 'CUSTOM', 'Personalizado'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    rol = models.CharField(
        max_length=20,
        choices=RolPredeterminado.choices,
        default=RolPredeterminado.ADMINISTRATIVO,
    )
    telefono = models.CharField(max_length=40, blank=True)
    debe_cambiar_password = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'perfil de usuario'
        verbose_name_plural = 'perfiles de usuario'

    def __str__(self):
        return f'{self.usuario.username} ({self.get_rol_display()})'
