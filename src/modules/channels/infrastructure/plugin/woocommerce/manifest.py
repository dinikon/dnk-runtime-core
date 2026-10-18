from pydantic import BaseModel, ConfigDict, Field
from src.modules.channels.application.plugin_contract import PluginManifestDTO


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


MANIFEST = PluginManifestDTO(
    "woocommerce",
    "WooCommerce",
    1,
    1,
    ("verify_connection", "read_publications"),
    WooCredentials.model_json_schema(),
    {
        "type": "string",
        "title": "Адрес магазина",
        "description": "HTTPS-адрес вашего магазина, например https://shop.example.",
        "format": "uri",
        "maxLength": 2048,
    },
)
