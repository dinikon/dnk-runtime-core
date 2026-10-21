"""Схема настроек принадлежит плагину и передаётся в Console без изменения ядра."""

from dataclasses import asdict, replace
from uuid import uuid4
import unittest
from pydantic import Field
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
from src.modules.channels.infrastructure.plugin.woocommerce.manifest import WooSettings
from src.modules.channels.presentation.channel.http.response.list_platforms import (
    ListPlatformsResponse,
)
from src.modules.channels.presentation.channel.http.response.get_platform_config import (
    GetPlatformConfigResponse,
)
from src.modules.channels.application.plugin_contract import (
    ResourceSettingsDTO,
    ConnectionSettingsReferencesDTO,
)
from src.modules.channels.domain.error import ChannelsValidationError


class ExtendedSettings(WooSettings):
    """Проверяет расширение плагина полем без SQL-колонки и общего условия."""

    batch_size: int = Field(ge=1, le=1000)


class ExtendedFactory(WooPluginFactory):
    """Объявляет собственную схему и проверку вместо изменения registry."""

    manifest = replace(
        WooPluginFactory.manifest,
        kind="custom-platform",
        settings_schema=ExtendedSettings.model_json_schema(),
    )

    def validate(
        self, settings: ResourceSettingsDTO, credentials: dict[str, str] | None
    ) -> ConnectionSettingsReferencesDTO:
        """Возвращает ссылки для общей проверки справочников."""
        parsed = ExtendedSettings.model_validate(settings.options)
        return ConnectionSettingsReferencesDTO(
            tuple(parsed.locales), (parsed.currency,)
        )


class ChannelsManifestTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет путь SDK → use-case DTO → отдельные HTTP-ответы."""

    async def test_settings_schema_reaches_both_http_contracts(self) -> None:
        """Manifest передаёт endpoint, схему значений и отдельную схему секретов."""
        registry = PluginRegistry((PromPluginFactory(), WooPluginFactory()))
        tenant = uuid4()
        response = ListPlatformsResponse(
            **asdict(
                await ListPlatformsHandler(registry).execute(ListPlatformsQuery(tenant))
            )
        )
        self.assertEqual(
            response.items[0].endpoint_schema["const"], "https://my.prom.ua"
        )
        self.assertNotIn("const", response.items[1].endpoint_schema)
        for item in response.items:
            self.assertEqual((item.sdk_version, item.config_version), (5, 3))
            detail = GetPlatformConfigResponse(
                **asdict(
                    await GetPlatformConfigHandler(registry).execute(
                        GetPlatformConfigQuery(tenant, item.kind)
                    )
                )
            )
            self.assertEqual(detail.manifest.model_dump(), item.model_dump())
            self.assertEqual(item.settings_schema["type"], "object")
            self.assertFalse(item.settings_schema["additionalProperties"])
            self.assertNotIn("settings_policy", item.model_dump())
            self.assertNotIn("publication_identity", item.model_dump())
            for field in item.credentials_schema["properties"].values():
                self.assertTrue(field["writeOnly"])
                self.assertNotIn("default", field)
        self.assertEqual(
            response.items[0].settings_schema["properties"]["currency"]["const"], "UAH"
        )

    async def test_identity_policy_is_an_optional_validated_plugin_capability(
        self,
    ) -> None:
        """Произвольный плагин подключает диагностику без ветвления ядра по kind."""
        original = replace(
            PromPluginFactory.manifest,
            capabilities=tuple(
                value
                for value in PromPluginFactory.manifest.capabilities
                if value != "batch_content_export"
            ),
        )
        factory = ExtendedFactory()
        factory.manifest = replace(original, kind="custom-identity")
        registry = PluginRegistry((factory,))
        self.assertEqual(
            registry.manifest("custom-identity").publication_identity,
            original.publication_identity,
        )
        for invalid in (
            replace(original, publication_identity=None),
            replace(
                original,
                capabilities=tuple(
                    value
                    for value in original.capabilities
                    if value != "publication_identity_diagnostics"
                ),
            ),
            replace(
                original,
                publication_identity=replace(
                    original.publication_identity, key_path=()
                ),
            ),
            replace(
                original,
                publication_identity=replace(
                    original.publication_identity, key_path=("provider", "")
                ),
            ),
        ):
            factory.manifest = invalid
            with self.assertRaises(ChannelsValidationError):
                PluginRegistry((factory,))

    async def test_plugin_validates_settings_and_returns_reference_codes(self) -> None:
        """Сохраняет действующие ограничения без локалей и валюты в общем VO."""
        registry = PluginRegistry((PromPluginFactory(), WooPluginFactory()))
        for kind, locales, currency in (
            ("prom", ["ru"], "UAH"),
            ("prom", ["ru", "uk"], "UAH"),
            ("woocommerce", ["uk"], "UAH"),
            ("woocommerce", ["en"], "USD"),
        ):
            settings = ResourceSettingsDTO(
                "https://my.prom.ua" if kind == "prom" else "https://shop.example",
                {"locales": locales, "currency": currency},
            )
            references = registry.validate(kind, settings, None)
            self.assertEqual(
                references, ConnectionSettingsReferencesDTO(tuple(locales), (currency,))
            )
        for kind, options in (
            ("prom", {"locales": ["uk"], "currency": "UAH"}),
            ("prom", {"locales": ["ru", "en"], "currency": "UAH"}),
            ("prom", {"locales": ["ru"], "currency": "USD"}),
            ("woocommerce", {"locales": ["uk", "ru"], "currency": "UAH"}),
            ("woocommerce", {"locales": [], "currency": "UAH"}),
            ("woocommerce", {"locales": ["uk"], "currency": None}),
            (
                "woocommerce",
                {"locales": ["uk"], "currency": "UAH", "token": "must-not-be-stored"},
            ),
        ):
            with (
                self.subTest(kind=kind, options=options),
                self.assertRaises(ChannelsValidationError),
            ):
                registry.validate(
                    kind,
                    ResourceSettingsDTO(
                        (
                            "https://my.prom.ua"
                            if kind == "prom"
                            else "https://shop.example"
                        ),
                        options,
                    ),
                    None,
                )

    async def test_new_plugin_can_extend_settings_without_core_changes(self) -> None:
        """Registry не зависит от набора полей конкретного плагина."""
        registry = PluginRegistry((ExtendedFactory(),))
        settings = ResourceSettingsDTO(
            "https://shop.example",
            {"locales": ["de"], "currency": "EUR", "batch_size": 250},
        )
        self.assertEqual(
            registry.validate("custom-platform", settings, None).currencies, ("EUR",)
        )
        self.assertIn(
            "batch_size",
            registry.manifest("custom-platform").settings_schema["properties"],
        )

    async def test_batch_factory_is_optional_and_declared_capability_requires_implementation(
        self,
    ) -> None:
        """Новая capability не заставляет Woo и сторонние read плагины иметь пустой exporter."""
        registry = PluginRegistry((PromPluginFactory(), WooPluginFactory()))
        self.assertIn("batch_content_export", registry.manifest("prom").capabilities)
        self.assertNotIn(
            "batch_content_export", registry.manifest("woocommerce").capabilities
        )
        factory = ExtendedFactory()
        factory.manifest = replace(
            factory.manifest,
            capabilities=(*factory.manifest.capabilities, "batch_content_export"),
        )
        with self.assertRaises(ChannelsValidationError):
            PluginRegistry((factory,))
