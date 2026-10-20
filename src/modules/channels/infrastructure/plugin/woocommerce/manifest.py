from pydantic import BaseModel, ConfigDict, Field
from src.modules.channels.application.plugin_contract import (
    PluginManifestDTO,
)


class WooCredentials(BaseModel):
    """Описывает только секретные поля подключения WooCommerce."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    consumer_key: str = Field(
        title="Ключ API",
        min_length=1,
        max_length=4096,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )
    consumer_secret: str = Field(
        title="Секрет API",
        min_length=1,
        max_length=4096,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )


class WooSettings(BaseModel):
    """Определяет язык и валюту Woo в расширяемой схеме настроек."""

    model_config = ConfigDict(
        title="Настройки ресурса",
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
    )
    locales: list[str] = Field(
        title="Языки ресурса",
        min_length=1,
        max_length=1,
        json_schema_extra={
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "x-reference": "locale"},
            "prefixItems": [
                {"type": "string", "title": "Основной язык", "x-reference": "locale"}
            ],
        },
    )
    currency: str = Field(
        title="Валюта ресурса",
        min_length=3,
        max_length=3,
        pattern="^[A-Z]{3}$",
        json_schema_extra={"x-reference": "currency"},
    )


MANIFEST = PluginManifestDTO(
    "woocommerce",
    "WooCommerce",
    5,
    3,
    (
        "verify_connection",
        "read_publications",
        "read_publication_details",
        "preview_content_update",
        "update_content",
    ),
    WooCredentials.model_json_schema(),
    {
        "type": "string",
        "title": "Адрес магазина",
        "description": "HTTPS-адрес вашего магазина, например https://shop.example.",
        "format": "uri",
        "maxLength": 2048,
    },
    WooSettings.model_json_schema(),
)
