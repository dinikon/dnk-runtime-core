from pathlib import Path
from typing import Self
from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings


class ChannelsSettings(BaseModel):
    """Настраивает шифрование credentials и ограничения внешнего чтения."""

    model_config = ConfigDict(hide_input_in_errors=True)
    credentials_encryption_key: SecretStr = Field(default=SecretStr(""), repr=False)
    credentials_encryption_key_path: str = ""
    http_timeout_seconds: int = Field(default=30, ge=1, le=120)
    max_response_bytes: int = Field(
        default=4 * 1024 * 1024, ge=1024, le=32 * 1024 * 1024
    )

    @model_validator(mode="after")
    def validate_key(self) -> Self:
        """Читает отдельный mounted secret и проверяет Fernet без раскрытия значения."""
        key = self.credentials_encryption_key.get_secret_value()
        if key and self.credentials_encryption_key_path:
            raise ValueError("Use CHANNELS encryption key or key path.")
        if self.credentials_encryption_key_path:
            try:
                key = Path(self.credentials_encryption_key_path).read_text().strip()
            except OSError:
                raise ValueError("Cannot read Channels encryption key file.") from None
        if key:
            try:
                Fernet(key.encode("ascii"))
            except (ValueError, UnicodeError):
                raise ValueError(
                    "Channels encryption key must be a Fernet key."
                ) from None
            self.credentials_encryption_key = SecretStr(key)
        return self


class ChannelsConfig(BaseSettings):
    """Подключает настройки Channels к общей deployment конфигурации."""

    CHANNELS: ChannelsSettings = Field(default_factory=ChannelsSettings)
