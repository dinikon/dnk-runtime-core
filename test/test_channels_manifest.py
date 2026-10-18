"""Контракт конфигурации Console остаётся декларативной частью read-плагина."""

from dataclasses import asdict
from uuid import uuid4
import unittest
from src.modules.channels.application.channel.query.list_platforms.handler import (
    ListPlatformsHandler,
)
from src.modules.channels.application.channel.query.list_platforms.query import (
    ListPlatformsQuery,
)
from src.modules.channels.application.channel.query.get_platform_config.handler import (
    GetPlatformConfigHandler,
)
from src.modules.channels.application.channel.query.get_platform_config.query import (
    GetPlatformConfigQuery,
)
from src.modules.channels.infrastructure.plugin.registry import PluginRegistry
from src.modules.channels.infrastructure.plugin.prom.factory import PromPluginFactory
from src.modules.channels.infrastructure.plugin.woocommerce.factory import (
    WooPluginFactory,
)
from src.modules.channels.presentation.channel.http.response.list_platforms import (
    ListPlatformsResponse,
)
from src.modules.channels.presentation.channel.http.response.get_platform_config import (
    GetPlatformConfigResponse,
)


class ChannelsManifestTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет SDK → use-case DTO → отдельные HTTP-ответы без секретных значений."""

    async def test_endpoint_metadata_reaches_both_http_contracts(self) -> None:
        """Prom фиксирует endpoint; Woo предоставляет поле адреса без UI-ветвлений."""
        registry = PluginRegistry((PromPluginFactory(), WooPluginFactory()))
        tenant = uuid4()
        result = await ListPlatformsHandler(registry).execute(
            ListPlatformsQuery(tenant)
        )
        response = ListPlatformsResponse(**asdict(result))
        self.assertEqual(
            response.items[0].endpoint_schema["const"], "https://my.prom.ua"
        )
        self.assertEqual(
            response.items[0].endpoint_schema["default"], "https://my.prom.ua"
        )
        self.assertNotIn("const", response.items[1].endpoint_schema)
        self.assertNotIn("default", response.items[1].endpoint_schema)
        for item in response.items:
            config = await GetPlatformConfigHandler(registry).execute(
                GetPlatformConfigQuery(tenant, item.kind)
            )
            detail = GetPlatformConfigResponse(**asdict(config))
            self.assertEqual(detail.manifest.model_dump(), item.model_dump())
            self.assertEqual(item.endpoint_schema["type"], "string")
            self.assertEqual(item.endpoint_schema["maxLength"], 2048)
            self.assertNotIn("credentials", item.model_dump())
            for field in item.credentials_schema["properties"].values():
                self.assertTrue(field["writeOnly"])
                self.assertNotIn("default", field)
