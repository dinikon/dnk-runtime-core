"""Reject integer primary keys in application-owned models, including M2M joins."""

from pathlib import Path
from django.apps import apps
from django.core.checks import Error, Tags, register
from django.db.models import UUIDField


@register(Tags.models)
def check_core_primary_keys(app_configs=None, **kwargs):
    """Check only local CORE apps, leaving third-party model contracts unchanged."""
    source_root = Path(__file__).resolve().parents[1]
    errors = []
    for config in app_configs if app_configs is not None else apps.get_app_configs():
        if not Path(config.path).resolve().is_relative_to(source_root):
            continue
        for model in config.get_models(include_auto_created=True):
            if not model._meta.proxy and not isinstance(model._meta.pk, UUIDField):
                errors.append(
                    Error(
                        "CORE models and their through tables must have UUID primary keys.",
                        hint="Use UUIDModel and an explicit UUID through model for ManyToManyField.",
                        obj=model,
                        id="core.E001",
                    )
                )
    return errors
