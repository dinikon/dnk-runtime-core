"""Load validated CORE configuration from its own dotenv file and process env."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from pydantic import ValidationError, model_validator
from pydantic_settings import SettingsConfigDict

from .configuration.application import ApplicationSettings
from .configuration.authentication import AuthenticationSettings
from .configuration.infrastructure import InfrastructureSettings
from .configuration.validation import validate_configuration

CORE_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_ENV_FILE = object()


class CoreSettings(ApplicationSettings, InfrastructureSettings, AuthenticationSettings):
    """Immutable settings with process variables taking precedence over CORE dotenv."""

    model_config = SettingsConfigDict(
        env_prefix="CORE_",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
        allow_inf_nan=False,
    )

    @model_validator(mode="after")
    def validate_policies(self):
        """Reject incompatible policies without accessing databases or providers."""
        validate_configuration(self)
        return self


def load_config(env_file=_DEFAULT_ENV_FILE, **overrides) -> CoreSettings:
    """Read only CORE dotenv; CORE_ENV_FILE='' opts out for tests or containers."""
    if env_file is _DEFAULT_ENV_FILE:
        selected = os.environ.get("CORE_ENV_FILE")
        env_file = (
            CORE_DIR / ".env"
            if selected is None
            else (Path(selected) if selected else None)
        )
    try:
        return CoreSettings(_env_file=env_file, **overrides)
    except ValidationError as exc:
        messages = []
        for error in exc.errors(
            include_input=False, include_context=False, include_url=False
        ):
            location = error["loc"]
            prefix = f"CORE_{str(location[0]).upper()}: " if location else ""
            messages.append(prefix + error["msg"])
        raise ImproperlyConfigured(
            "Invalid CORE configuration: " + "; ".join(messages)
        ) from None
    except (OSError, UnicodeError):
        raise ImproperlyConfigured("Cannot read the selected CORE_ENV_FILE.") from None
