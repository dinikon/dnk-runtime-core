from pydantic import BaseModel, ConfigDict, Field
from src.modules.channels.application.plugin_contract import PluginManifestDTO


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


MANIFEST = PluginManifestDTO(
    "prom",
    "Prom.ua",
    1,
    1,
    ("verify_connection", "read_publications"),
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
)
