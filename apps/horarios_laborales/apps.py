from django.apps import AppConfig


class HorariosLaboralesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.horarios_laborales'
    verbose_name = 'Horarios laborales'

    def ready(self):
        from . import signals  # noqa: F401
