"""Валюта, языки контента, совместимость настроек и справочники Channels."""

from dataclasses import asdict
import unittest
from itertools import product
from unittest.mock import AsyncMock

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.infrastructure.persistence.mapper import (
    to_domain,
    to_read_row,
    write_verification,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.infrastructure.settings_catalog import (
    ReferenceDataChannelSettings,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)
from test import test_channels_domain as support


class ConnectionSettingsTests(unittest.TestCase):
    """Конкретные пакеты владеют настройками и их схемами."""

    def test_defaults_and_concrete_settings_schemas(self) -> None:
        """Пустые legacy-настройки получают defaults без изменения входного VO."""
        for kind, endpoint in (
            ("prom", "https://my.prom.ua"),
            ("rozetka", "https://api-seller.rozetka.com.ua"),
            ("woocommerce", "https://shop.example"),
        ):
            with self.subTest(kind=kind):
                platform = InstalledPlatforms().get(kind)
                source = ConnectionConfigVO.create(
                    version=1, endpoint=endpoint, settings={}
                )
                result = platform.validate(source, None)
                expected = (
                    {"currency": "UAH", "locale": "uk"}
                    if kind == "woocommerce"
                    else {"currency": "UAH", "locales": ["ru", "uk"]}
                )
                self.assertEqual(result.config.settings, expected)
                self.assertEqual(source.settings, {})
                self.assertEqual(result.currency, "UAH")
                self.assertEqual(
                    result.locales, ("uk",) if kind == "woocommerce" else ("ru", "uk")
                )
                self.assertEqual(
                    platform.manifest.supported_capabilities, ("verify_connection",)
                )
                schema = platform.manifest.config_schema
                reference = schema["properties"]["settings"]["$ref"].split("/")[-1]
                fields = schema["$defs"][reference]["properties"]
                if kind == "woocommerce":
                    self.assertEqual(fields["currency"]["enum"], ["UAH", "EUR", "USD"])
                    self.assertEqual(fields["locale"]["enum"], ["uk", "ru", "en"])
                    self.assertNotIn("locales", fields)
                else:
                    self.assertEqual(fields["currency"]["const"], "UAH")
                    self.assertTrue(fields["locales"]["readOnly"])
                    self.assertIn("основной", fields["locales"]["description"])

    def test_fixed_languages_are_normalized_without_mutating_input(self) -> None:
        """Оба порядка входного JSON дают русский основным, а украинский дополнительным."""
        for kind, endpoint in (
            ("prom", "https://my.prom.ua"),
            ("rozetka", "https://api-seller.rozetka.com.ua"),
        ):
            for locales in (["ru", "uk"], ["uk", "ru"]):
                platform = InstalledPlatforms().get(kind)
                original = list(locales)
                result = platform.validate(
                    ConnectionConfigVO.create(
                        version=1,
                        endpoint=endpoint,
                        settings={"currency": "UAH", "locales": locales},
                    ),
                    None,
                )
                self.assertEqual(
                    result.config.settings, {"currency": "UAH", "locales": ["ru", "uk"]}
                )
                self.assertEqual(locales, original)

    def test_fixed_platforms_reject_partial_duplicate_or_unknown_languages(
        self,
    ) -> None:
        """Фиксированный набор не позволяет случайно выключить перевод или изменить валюту."""
        for kind, endpoint in (
            ("prom", "https://my.prom.ua"),
            ("rozetka", "https://api-seller.rozetka.com.ua"),
        ):
            for settings in (
                {"currency": "EUR"},
                {"currency": "USD"},
                {"currency": "uah"},
                *(
                    {"locales": locales}
                    for locales in (
                        [],
                        ["ru"],
                        ["ru", "ru"],
                        ["ru", "ua"],
                        ["ru", "en"],
                        ["ru", "uk", "en"],
                        "ru,uk",
                        None,
                        ["ru", {}],
                    )
                ),
                {"locale": "ru"},
                {"stock_sync": {"allow_export": True}},
            ):
                with (
                    self.subTest(kind=kind, settings=settings),
                    self.assertRaises(ChannelInputError) as error,
                ):
                    InstalledPlatforms().get(kind).validate(
                        ConnectionConfigVO.create(
                            version=1, endpoint=endpoint, settings=settings
                        ),
                        None,
                    )
                self.assertEqual(error.exception.code, "configuration_invalid")

    def test_woocommerce_accepts_each_single_currency_and_locale(self) -> None:
        """Все девять комбинаций сохраняются без преобразования в мультиязычный набор."""
        platform = InstalledPlatforms().get("woocommerce")
        for currency, locale in product(("UAH", "EUR", "USD"), ("uk", "ru", "en")):
            settings = {"currency": currency, "locale": locale}
            with self.subTest(settings=settings):
                result = platform.validate(
                    ConnectionConfigVO.create(
                        version=1, endpoint="https://shop.example", settings=settings
                    ),
                    None,
                )
                self.assertEqual(result.config.settings, settings)
                self.assertEqual(
                    (result.currency, result.locales), (currency, (locale,))
                )
        for settings in (
            {"currency": "GBP"},
            {"currency": ["UAH", "EUR"]},
            {"locale": "ua"},
            {"locale": ["uk", "ru"]},
            {"locales": ["uk"]},
            {"stock_sync": {}},
        ):
            with self.subTest(settings=settings), self.assertRaises(ChannelInputError):
                platform.validate(
                    ConnectionConfigVO.create(
                        version=1, endpoint="https://shop.example", settings=settings
                    ),
                    None,
                )

    def test_mapper_roundtrip_has_no_retired_policy_and_preserves_secret(self) -> None:
        """Mapper восстанавливает только принадлежащие Channel данные подключения."""
        fixture = support.ChannelsDomainTests()
        fixture.setUp()
        value = fixture.channel
        row = ChannelModel(
            id=value.id.uuid,
            name=value.name.value,
            platform_kind=value.platform_kind,
            revision=value.revision,
            created_by=value.created_by.uuid,
            updated_by=value.updated_by.uuid,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )
        c = value.connection
        stored = ConnectionModel(
            id=c.id.uuid,
            channel_id=value.id.uuid,
            config_version=c.config.version,
            endpoint=c.config.endpoint,
            settings={},
            encrypted_credentials=c.encrypted_credentials,
            config_revision=c.config_revision,
            identity_namespace=None,
            identity_key=None,
            verification=write_verification(c.verification),
        )
        restored = to_domain(row, stored)
        self.assertEqual(asdict(restored), asdict(value))
        public = to_read_row(row, stored)
        self.assertEqual(public.config.settings, {})
        self.assertNotIn("credentials", repr(public))
        self.assertFalse(hasattr(restored.connection, "stock_sync"))


class ReferenceDataChannelSettingsTests(unittest.IsolatedAsyncioTestCase):
    """Отказы публичных справочников преобразуются в безопасные ошибки Channels."""

    async def test_validates_currency_and_each_requested_locale(self) -> None:
        """Проверяет только запрошенные языки через Application-порт владельца."""
        currencies = AsyncMock(spec=ValidateCurrencyHandler)
        locales = AsyncMock(spec=CatalogRepositoryPort)
        locales.has_active_locale.return_value = True
        await ReferenceDataChannelSettings(currencies, locales).ensure_available(
            currency="UAH", locales=("ru", "uk")
        )
        self.assertEqual(currencies.execute.await_args.args[0].code, "UAH")
        self.assertEqual(
            [call.args[0] for call in locales.has_active_locale.await_args_list],
            ["ru", "uk"],
        )

    async def test_currency_failure_is_safe_and_skips_locale_queries(self) -> None:
        """Недоступная валюта не раскрывает внутреннее сообщение справочника."""
        currencies = AsyncMock(spec=ValidateCurrencyHandler)
        currencies.execute.side_effect = CurrencyCodeNotSupportedError(
            "secret-internal-detail"
        )
        locales = AsyncMock(spec=CatalogRepositoryPort)
        with self.assertRaises(ChannelInputError) as error:
            await ReferenceDataChannelSettings(currencies, locales).ensure_available(
                currency="UAH", locales=("ru", "uk")
            )
        self.assertEqual(error.exception.code, "currency_unavailable")
        self.assertEqual(error.exception.field, "config.settings.currency")
        self.assertNotIn("secret", str(error.exception))
        locales.has_active_locale.assert_not_awaited()

    async def test_inactive_locale_is_rejected(self) -> None:
        """Валюта может быть доступна, но язык всё равно обязан существовать."""
        currencies = AsyncMock(spec=ValidateCurrencyHandler)
        locales = AsyncMock(spec=CatalogRepositoryPort)
        locales.has_active_locale.return_value = False
        with self.assertRaises(ChannelInputError) as error:
            await ReferenceDataChannelSettings(currencies, locales).ensure_available(
                currency="EUR", locales=("en",)
            )
        self.assertEqual(error.exception.code, "locale_unavailable")
        self.assertEqual(error.exception.field, "config.settings")
