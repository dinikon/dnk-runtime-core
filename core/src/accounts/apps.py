from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Register the stable accounts app label and Django model defaults."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Аккаунты"
