from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _on_post_migrate(sender, app_config=None, **kwargs):
    """Crea usuarios hardcodeados, roles y datos base al terminar migrate."""
    if app_config is None or app_config.name != "apps.accounts":
        return
    from .bootstrap import ejecutar_bootstrap
    ejecutar_bootstrap()


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Cuentas y usuarios"

    def ready(self):
        post_migrate.connect(_on_post_migrate, dispatch_uid="accounts.bootstrap")
