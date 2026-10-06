from typing import Any
from copy import deepcopy
from src.modules.channels.application.port.registry import ChannelDefinition
from src.modules.channels.domain.value_object.kind import ChannelKind
from src.modules.channels.domain.value_object.channel_type import ChannelType
from src.modules.channels.domain.error import ChannelNotFoundError

PLATFORMS = [
    ("etsy", "marketplace", "Etsy"),
    ("amazon", "marketplace", "Amazon"),
    ("ebay", "marketplace", "eBay"),
    ("prom", "marketplace", "Prom.ua"),
    ("rozetka", "marketplace", "Rozetka.com.ua"),
    ("allo", "marketplace", "Allo"),
    ("kasta", "marketplace", "Kasta"),
    ("epicentr", "marketplace", "Эпицентр"),
    ("shopify", "shop", "Shopify"),
    ("horoshop", "shop", "Хорошоп"),
    ("tilda", "shop", "Tilda"),
    ("wix", "shop", "Wix"),
    ("weblium", "shop", "Weblium"),
    ("shop_express", "shop", "Shop-Express"),
    ("webflow", "shop", "Webflow"),
    ("opencart", "cms", "OpenCart"),
    ("woocommerce", "cms", "WooCommerce"),
    ("magento", "cms", "Magento CMS"),
    ("prestashop", "cms", "PrestaShop CMS"),
    ("okay_cms", "cms", "Okay CMS"),
    ("cs_cart", "cms", "CS-Cart"),
]


def connection(fields: list[tuple[str, str, bool]]) -> dict[str, Any]:
    """Собирает опубликованную схему подключения из подтверждённых полей."""
    return {
        "json_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                key: dict(
                    type="string",
                    title=label,
                    minLength=1,
                    maxLength=4096,
                    **(
                        {"writeOnly": True} if secret else {"format": "https-store-url"}
                    ),
                )
                for key, label, secret in fields
            },
            "required": [key for key, _, _ in fields],
            "additionalProperties": False,
        },
        "ui_schema": [
            {
                "property": key,
                "widget": "password" if secret else "url",
                "help_text": "",
            }
            for key, _, secret in fields
        ],
    }


CONNECTIONS = {
    "prom": connection([("api_key", "API key", True)]),
    "woocommerce": connection(
        [
            ("url", "Адрес магазина", False),
            ("consumer_key", "Consumer key", True),
            ("consumer_secret", "Consumer secret", True),
        ]
    ),
}


class CodeChannelRegistry:
    """Реестр выдаёт копии: вызывающий код не меняет определения платформ."""

    def list_all(self) -> tuple[ChannelDefinition, ...]:
        """Возвращает независимые определения всех платформ в порядке каталога."""
        return tuple(self.get(kind) for kind, _, _ in PLATFORMS)

    def get(self, kind: str) -> ChannelDefinition:
        """Возвращает копию конфигурации либо безопасную ошибку отсутствия."""
        row = next((row for row in PLATFORMS if row[0] == kind), None)
        if row is None:
            raise ChannelNotFoundError("Platform not found.")
        key, category, label = row
        enabled = key in CONNECTIONS
        return ChannelDefinition(
            ChannelKind(key),
            ChannelType(category),
            label,
            enabled,
            None if enabled else "Настройка этой платформы пока недоступна.",
            1,
            {"connection": deepcopy(CONNECTIONS.get(key)), "capabilities": {}},
        )
