from django.apps import AppConfig


class SancionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sanciones'
    verbose_name = 'Sanciones'

    def ready(self):
        from . import signals  # noqa: F401
