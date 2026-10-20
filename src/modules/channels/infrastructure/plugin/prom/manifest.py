from src.modules.channels.infrastructure.plugin.prom.identity import IDENTITY_POLICY
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.modules.channels.application.plugin_contract import (
    PluginManifestDTO,
)


class PromCredentials(BaseModel):
    """Описывает только секретные поля подключения Prom.ua."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    token: str = Field(
        title="Токен API",
        min_length=1,
        max_length=4096,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )


class PromSettings(BaseModel):
    """Определяет несекретные настройки Prom и их JSON Schema."""

    model_config = ConfigDict(
        title="Настройки ресурса",
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
    )
    locales: list[str] = Field(
        title="Языки ресурса",
        min_length=1,
        max_length=2,
        json_schema_extra={
            "uniqueItems": True,
            "default": ["ru"],
            "items": {"type": "string", "enum": ["ru", "uk"], "x-reference": "locale"},
            "prefixItems": [
                {
                    "type": "string",
                    "const": "ru",
                    "title": "Основной язык",
                    "x-reference": "locale",
                },
                {
                    "type": "string",
                    "enum": ["uk"],
                    "title": "Дополнительный язык",
                    "x-reference": "locale",
                },
            ],
        },
    )
    currency: str = Field(
        title="Валюта ресурса",
        json_schema_extra={"const": "UAH", "default": "UAH", "x-reference": "currency"},
    )

    @model_validator(mode="after")
    def check_policy(self) -> "PromSettings":
        """Не допускает конфигурацию, которую Prom не поддерживает."""
        if self.locales not in (["ru"], ["ru", "uk"]) or self.currency != "UAH":
            raise ValueError("unsupported_prom_settings")
        return self


MANIFEST = PluginManifestDTO(
    "prom",
    "Prom.ua",
    5,
    3,
    (
        "verify_connection",
        "read_publications",
        "read_publication_details",
        "preview_content_update",
        "publication_identity_diagnostics",
    ),
    PromCredentials.model_json_schema(),
    {
        "type": "string",
        "title": "Адрес API",
        "description": "Адрес API Prom.ua фиксирован для всех магазинов.",
        "format": "uri",
        "maxLength": 2048,
        "default": "https://my.prom.ua",
        "const": "https://my.prom.ua",
    },
    PromSettings.model_json_schema(),
    publication_identity=IDENTITY_POLICY,
)
