from typing import Literal
from pydantic import BaseModel, Field, SecretStr, field_validator
from src.modules.channels.infrastructure.platforms.base import StrictModel
from src.modules.channels.infrastructure.platforms.url import normalize_endpoint


class WooCommerceSettings(StrictModel):
    """Дополнительных настроек для проверки WooCommerce нет."""


class WooCommerceConfig(StrictModel):
    """Публичный HTTPS URL магазина с возможным подпутём WordPress."""

    version: Literal[1] = 1
    endpoint: str = Field(title="Адрес магазина", json_schema_extra={"format": "uri"})
    settings: WooCommerceSettings = Field(default_factory=WooCommerceSettings)

    @field_validator("endpoint")
    @classmethod
    def normalize(cls, value: str) -> str:
        """Проверяет синтаксис base URL до сохранения credentials."""
        return normalize_endpoint(value)


class WooCommerceCredentials(StrictModel):
    """Ключи REST API WooCommerce."""

    consumer_key: SecretStr = Field(min_length=1, max_length=4096, title="Consumer key")
    consumer_secret: SecretStr = Field(
        min_length=1, max_length=4096, title="Consumer secret"
    )


class WooEnvironment(BaseModel):
    """Только canonical URL установки из защищённого ответа."""

    site_url: str


class WooSystemStatus(BaseModel):
    """Минимальный результат проверки system_status."""

    environment: WooEnvironment
