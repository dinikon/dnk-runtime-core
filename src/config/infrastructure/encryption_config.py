"""Единственный постоянный ключ шифрования проекта и совместимость настроек."""

from collections.abc import Callable, Mapping
import base64
from pathlib import Path
from typing import Self

from cryptography.fernet import Fernet
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


class EncryptionSettings(BaseModel):
    """Один Fernet-ключ из значения или файла для API и всех worker."""

    model_config = ConfigDict(hide_input_in_errors=True, extra="forbid")

    key: SecretStr | None = Field(default=None, repr=False)
    key_path: str = ""
    _file_key: SecretStr | None = PrivateAttr(default=None)

    @property
    def resolved_key(self) -> SecretStr | None:
        """Возвращает единственный разрешённый ключ без повторного чтения файла."""
        return self.key if self.key is not None else self._file_key

    @model_validator(mode="after")
    def resolve_key(self) -> Self:
        """Читает постоянный ключ и проверяет формат, не выводя его значение."""
        if self.key is not None and not self.key.get_secret_value():
            self.key = None
        if self.key is not None and self.key_path:
            raise ValueError("Use ENCRYPTION key OR key_path")
        if self.key_path:
            try:
                value = Path(self.key_path).read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError):
                raise ValueError("Cannot read project encryption key file") from None
            if not value:
                raise ValueError("Project encryption key file is empty")
            self._file_key = SecretStr(value)
        else:
            self._file_key = None
        if self.resolved_key is not None:
            try:
                Fernet(self.resolved_key.get_secret_value().encode("ascii"))
            except (ValueError, UnicodeError):
                raise ValueError(
                    "Project encryption key must be a Fernet key"
                ) from None
        return self


class EncryptionConfig(BaseSettings):
    """Подключает общую конфигурацию и сводит прежние имена к одному ключу."""

    ENCRYPTION: EncryptionSettings = Field(default_factory=EncryptionSettings)

    @model_validator(mode="before")
    @classmethod
    def collect_legacy_keys(cls, values: object) -> object:
        """Не выбирает молча один из разных ключей существующих модулей."""
        if not isinstance(values, Mapping):
            return values
        data = dict(values)
        candidates: list[EncryptionSettings] = []
        configured = data.get("ENCRYPTION")
        if configured:
            # Сохраняем уже проверенную модель вместе с разрешённым файловым ключом.
            candidates.append(
                configured
                if isinstance(configured, EncryptionSettings)
                else EncryptionSettings.model_validate(configured)
            )
        control_plane = data.get("CONTROL_PLANE")
        if isinstance(control_plane, Mapping):
            legacy = {str(key).lower(): value for key, value in control_plane.items()}
            candidates.append(
                EncryptionSettings(
                    key=legacy.get("secret_encryption_key"),
                    key_path=legacy.get("encryption_key_path") or "",
                )
            )
        channels = data.pop("CHANNELS", None)
        if isinstance(channels, Mapping):
            legacy = {str(key).lower(): value for key, value in channels.items()}
            candidates.append(
                EncryptionSettings(key=legacy.get("credentials_encryption_key"))
            )
        legacy_env = data.pop("_legacy_encryption", {})
        if isinstance(legacy_env, Mapping):
            candidates.extend(
                EncryptionSettings.model_validate(candidate)
                for candidate in legacy_env.values()
            )
        configured_keys = [
            candidate for candidate in candidates if candidate.resolved_key is not None
        ]
        if configured_keys:
            first = configured_keys[0]
            assert first.resolved_key is not None
            identity = base64.urlsafe_b64decode(first.resolved_key.get_secret_value())
            if any(
                base64.urlsafe_b64decode(candidate.resolved_key.get_secret_value())
                != identity
                for candidate in configured_keys[1:]
                if candidate.resolved_key is not None
            ):
                raise ValueError(
                    "Conflicting project encryption keys; preserve the existing key and consolidate encryption settings"
                )
            data["ENCRYPTION"] = first
        return data


def legacy_encryption_source(
    env_source: PydanticBaseSettingsSource,
    dotenv_source: PydanticBaseSettingsSource,
) -> Callable[[], dict[str, object]]:
    """Читает только прежние имена, не заменяя штатные источники BaseSettings."""

    def load() -> dict[str, object]:
        """Сохраняет приоритет env над dotenv и не выводит значения секретов."""
        env = {
            **getattr(dotenv_source, "env_vars", {}),
            **getattr(env_source, "env_vars", {}),
        }
        legacy: dict[str, object] = {}
        channels_key = env.get("channels__credentials_encryption_key")
        if channels_key:
            legacy["channels"] = {"key": channels_key}
        cp_key = env.get("control_plane__secret_encryption_key")
        cp_path = env.get("control_plane__encryption_key_path")
        if cp_key or cp_path:
            legacy["control_plane"] = {"key": cp_key or None, "key_path": cp_path or ""}
        return {"_legacy_encryption": legacy} if legacy else {}

    return load
