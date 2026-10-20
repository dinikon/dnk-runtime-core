from unittest.mock import AsyncMock, patch
import asyncio
import socket
import httpx
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

"Предметные инварианты и контракт read-only плагинов Channels."
from dataclasses import fields
from datetime import UTC, date, datetime
from decimal import Decimal
import unittest
from uuid import uuid4
from cryptography.fernet import Fernet
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.value_object.settings import (
    ConnectionSettingsVO,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
    ChannelsUnavailableError,
)
from src.modules.channels.domain.sync_run.aggregate import SyncRun
from src.modules.channels.application.plugin_contract import (
    ResourceSettingsDTO,
    ReadPublicationPageInputDTO,
    HttpResultDTO,
    ConnectionCredentialsDTO,
    VerifyConnectionInputDTO,
)
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.infrastructure.security.credentials import ConnectionSecrets
from src.modules.channels.infrastructure.plugin.woocommerce.core_normalizer import (
    normalize_product as woo_normalize,
)
from src.modules.channels.infrastructure.plugin.prom.core_normalizer import (
    normalize_product as prom_normalize,
)
from src.modules.channels.infrastructure.plugin.woocommerce.read_publication_page import (
    WooReadPublicationPagePlugin,
)
from src.modules.channels.infrastructure.plugin.prom.read_publication_page import (
    PromReadPublicationPagePlugin,
)
from src.modules.channels.infrastructure.http.transport import ScopedHttpTransport
from src.modules.channels.infrastructure.plugin.registry import PluginRegistry
from src.modules.channels.infrastructure.plugin.prom.factory import PromPluginFactory
from src.modules.channels.infrastructure.plugin.prom.verify_connection import (
    PromVerifyConnectionPlugin,
)
from src.modules.channels.infrastructure.plugin.woocommerce.verify_connection import (
    WooVerifyConnectionPlugin,
)


class ChannelsDomainTests(unittest.TestCase):
    """Защищает границы одного источника и независимого observed состояния."""

    def setUp(self) -> None:
        """Создаёт отключённый источник и явные ресурсные настройки."""
        self.now, self.actor = (datetime.now(UTC), EntityIdVO.from_value(uuid4()))
        self.channel = Channel.create(
            EntityIdVO.from_value(uuid4()),
            " Shop ",
            "woocommerce",
            self.actor,
            self.now,
        )
        self.settings = ConnectionSettingsVO(
            "https://shop.example", {"locales": ["uk"], "currency": "UAH"}
        )

    def test_single_connection_and_default_off(self) -> None:
        """Второй Connection запрещён независимо от первой проверки и архива."""
        self.assertFalse(self.channel.is_enabled)
        self.channel.attach_connection(
            EntityIdVO.from_value(uuid4()),
            self.settings,
            "encrypted",
            self.actor,
            self.now,
        )
        with self.assertRaises(ChannelsConflictError):
            self.channel.attach_connection(
                EntityIdVO.from_value(uuid4()),
                self.settings,
                "other",
                self.actor,
                self.now,
            )
        self.channel.archive(self.actor, self.now)
        with self.assertRaises(ChannelsConflictError):
            self.channel.attach_connection(
                EntityIdVO.from_value(uuid4()),
                self.settings,
                "other",
                self.actor,
                self.now,
            )

    def test_verified_identity_rotation_and_generation(self) -> None:
        """Кандидат не подменяет ключ, stale verification не применяется."""
        self.channel.attach_connection(
            EntityIdVO.from_value(uuid4()), self.settings, "first", self.actor, self.now
        )
        self.channel.request_verification(
            EntityIdVO.from_value(uuid4()), self.actor, self.now
        )
        self.channel.apply_verification(1, "site:shop", None, (), self.actor, self.now)
        self.channel.update_connection(self.settings, "candidate", self.actor, self.now)
        self.assertEqual(self.channel.connection.credentials_ciphertext, "first")
        self.channel.request_verification(
            EntityIdVO.from_value(uuid4()), self.actor, self.now
        )
        with self.assertRaises(ChannelsConflictError):
            self.channel.apply_verification(
                1, "site:shop", None, (), self.actor, self.now
            )
        self.channel.apply_verification(
            self.channel.connection.generation,
            "site:other",
            None,
            (),
            self.actor,
            self.now,
        )
        self.assertEqual(self.channel.connection.resource_identity, "site:shop")
        self.assertEqual(self.channel.connection.credentials_ciphertext, "first")
        self.assertEqual(self.channel.connection.verification_status, "error")

    def test_pause_and_restore_keep_domain_rules(self) -> None:
        """Пауза запрещает сеть, восстановление не обходит инварианты."""
        self.channel.attach_connection(
            EntityIdVO.from_value(uuid4()),
            self.settings,
            "cipher",
            self.actor,
            self.now,
        )
        self.channel.request_verification(
            EntityIdVO.from_value(uuid4()), self.actor, self.now
        )
        self.channel.apply_verification(1, "site:test", None, (), self.actor, self.now)
        self.channel.ensure_network()
        self.channel.pause_connection(self.actor, self.now)
        with self.assertRaises(ChannelsUnavailableError):
            self.channel.ensure_network()
        values = {
            item.name: getattr(self.channel, item.name) for item in fields(self.channel)
        }
        values["identifier"] = values.pop("id")
        self.assertEqual(
            Channel.restore(**values).connection.id, self.channel.connection.id
        )
        values["name"] = ""
        with self.assertRaises(ChannelsValidationError):
            Channel.restore(**values)

    def test_run_replay_progress_and_bounded_retry(self) -> None:
        """Повтор страницы не продвигает checkpoint, retry имеет конечный предел."""
        run = SyncRun.create(
            EntityIdVO.from_value(uuid4()),
            EntityIdVO.from_value(self.channel.id),
            EntityIdVO.from_value(uuid4()),
            1,
            EntityIdVO.from_value(self.actor),
            EntityIdVO.from_value(uuid4()),
            (),
            self.now,
        )
        run.ensure_step(0)
        run.advance({"page": 2}, 2, 0, False, self.now)
        with self.assertRaises(ChannelsConflictError):
            run.ensure_step(0)
        with self.assertRaises(ChannelsConflictError):
            run.advance({"page": 2}, 2, 0, False, self.now)
        for _ in range(3):
            self.assertTrue(run.fail("network_error", self.now, True))
        self.assertFalse(run.fail("network_error", self.now, True))
        self.assertEqual(run.status, "partial")
        self.assertEqual(run.processed, 2)

    def test_secrets_are_scoped_and_never_in_repr(self) -> None:
        """Ciphertext другого tenant/Connection не раскрывает credentials."""
        secrets = ConnectionSecrets(Fernet.generate_key().decode())
        tenant, connection = (uuid4(), uuid4())
        ciphertext = secrets.seal(tenant, connection, {"token": "sensitive"})
        dto = secrets.open(tenant, connection, ciphertext)
        self.assertNotIn("sensitive", repr(dto))
        with self.assertRaises(PluginCallError):
            secrets.open(uuid4(), connection, ciphertext)
        with self.assertRaises(PluginCallError):
            secrets.open(tenant, uuid4(), ciphertext)

    def test_plugin_registration_rejects_duplicates(self) -> None:
        """Дополнительный plugin не требует изменения центрального enum."""
        with self.assertRaises(ChannelsValidationError):
            PluginRegistry((PromPluginFactory(), PromPluginFactory()))
        self.assertEqual(
            PluginRegistry((PromPluginFactory(),)).manifests()[0].kind, "prom"
        )

    def test_core_keeps_decimal_zero_and_unknown_values(self) -> None:
        """Core различает отсутствующую цену, нулевое количество и плохие optional поля."""
        settings = ResourceSettingsDTO(
            "https://shop.example", {"locales": ["uk"], "currency": "UAH"}
        )
        row = woo_normalize(
            {
                "id": 10,
                "name": "<b>Name</b>",
                "regular_price": "123.450000000001",
                "sale_price": "0",
                "stock_quantity": 0,
                "stock_status": "outofstock",
                "images": [{"src": "javascript:bad"}],
            },
            settings,
        )
        self.assertEqual(row.core.price, Decimal("123.450000000001"))
        self.assertEqual(row.core.sale_price, Decimal(0))
        self.assertEqual(row.core.quantity, Decimal(0))
        self.assertIsNone(row.core.main_image_url)
        self.assertEqual(row.core.title, "Name")
        bad = woo_normalize(
            {
                "id": 11,
                "regular_price": "NaN",
                "stock_quantity": True,
                "stock_status": {},
            },
            settings,
        )
        self.assertIsNone(bad.core.price)
        self.assertIsNone(bad.core.quantity)
        self.assertEqual(bad.core.stock_status, "unknown")
        prom = prom_normalize(
            {
                "id": 99,
                "external_id": "import-77",
                "price": Decimal("20.21"),
                "currency": "₴",
                "discount": {"value": 10, "type": "percent"},
            },
            ResourceSettingsDTO(
                "https://my.prom.ua", {"locales": ["ru"], "currency": "UAH"}
            ),
            observed_on=date(2026, 10, 18),
        )
        self.assertEqual(prom.core.external_id, "99")
        self.assertIsNone(prom.core.sale_price)
        self.assertIsNone(prom.core.currency)
        self.assertIsNone(prom.core.quantity)
        self.assertIn("invalid_sale_price", prom.core.warnings)

    def test_prom_stock_quantity_preserves_zero_and_decimal_precision(self) -> None:
        """Исходный остаток сохраняется без округления и независимо от наличия."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
        )
        for source, expected in (
            (0, Decimal(0)),
            (17, Decimal(17)),
            ("2.7500", Decimal("2.7500")),
            (Decimal("1.234567890123"), Decimal("1.234567890123")),
        ):
            with self.subTest(source=source):
                publication = prom_normalize(
                    {"id": 99, "quantity_in_stock": source, "presence": "available"},
                    settings,
                    observed_on=date(2026, 10, 18),
                )
                self.assertEqual(publication.core.quantity, expected)
                self.assertEqual(publication.core.stock_status, "in_stock")
                self.assertNotIn("quantity_not_exposed", publication.core.warnings)
                self.assertNotIn("invalid_quantity", publication.core.warnings)

    def test_prom_unavailable_quantity_is_not_inferred_from_availability(self) -> None:
        """Отсутствующий остаток не вычисляется из наличия и минимального заказа."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
        )
        for extra in ({}, {"quantity_in_stock": None}, {"quantity_in_stock": ""}):
            with self.subTest(extra=extra):
                publication = prom_normalize(
                    {
                        "id": 99,
                        "presence": "available",
                        "in_stock": True,
                        "minimum_order_quantity": 5,
                        **extra,
                    },
                    settings,
                    observed_on=date(2026, 10, 18),
                )
                self.assertIsNone(publication.core.quantity)
                self.assertIn("quantity_not_exposed", publication.core.warnings)

    def test_prom_invalid_quantity_keeps_publication_with_warning(self) -> None:
        """Повреждённое optional количество не превращается в ноль или отказ страницы."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
        )
        for source in (True, False, "bad", "NaN", "Infinity", "1e18", "1e-13"):
            with self.subTest(source=source):
                publication = prom_normalize(
                    {"id": 99, "quantity_in_stock": source},
                    settings,
                    observed_on=date(2026, 10, 18),
                )
                self.assertIsNone(publication.core.quantity)
                self.assertIn("invalid_quantity", publication.core.warnings)
                self.assertEqual(publication.core.external_id, "99")


class CredentialsFixture:
    """Выдаёт только тестовый scoped набор секретов."""

    async def resolve(self) -> ConnectionCredentialsDTO:
        """Возвращает несекретные fixture значения."""
        return ConnectionCredentialsDTO(
            {"token": "test", "consumer_key": "key", "consumer_secret": "secret"}
        )


class RepeatingTransport:
    """Симулирует API, игнорирующий cursor/page."""

    async def get(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Возвращает одну и ту же identity независимо от параметров."""
        return HttpResultDTO(
            (
                [{"id": 10, "name": "Test"}]
                if "wp-json" in path
                else {"groups": [{"id": 10}]}
            ),
            {},
        )


class ChannelsPluginTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет bounded cursors и сетевые ограничения без реального кабинета."""

    async def test_scoped_transport_forwards_explicit_language_header(self) -> None:
        """SDK разрешает язык ответа, сохраняя закреплённый origin и публичный IP."""

        def response(request: httpx.Request) -> httpx.Response:
            """Проверяет заголовки без настоящего сетевого запроса."""
            self.assertEqual(request.headers["X-LANGUAGE"], "ru")
            self.assertEqual(request.headers["Host"], "my.prom.ua")
            self.assertEqual(request.url.host, "8.8.8.8")
            return httpx.Response(200, json={"products": []})

        client = httpx.AsyncClient(transport=httpx.MockTransport(response))
        with (
            patch.object(
                asyncio.get_running_loop(),
                "getaddrinfo",
                AsyncMock(
                    return_value=[
                        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
                    ]
                ),
            ),
            patch(
                "src.modules.channels.infrastructure.http.transport.httpx.AsyncClient",
                return_value=client,
            ),
        ):
            result = await ScopedHttpTransport("https://my.prom.ua").get(
                "/api/v1/products/list", headers={"X-LANGUAGE": "ru"}
            )
        self.assertEqual(result.body, {"products": []})

    async def test_prom_requests_the_configured_primary_language(self) -> None:
        """Язык названия не зависит от украинского default API Prom."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru", "uk")), "currency": "UAH"}
        )
        transport = RepeatingTransport()
        with patch.object(
            transport,
            "get",
            AsyncMock(
                return_value=HttpResultDTO(
                    {"products": [{"id": 10, "name": "Название"}]}, {}
                )
            ),
        ) as get:
            outcome = await PromReadPublicationPagePlugin(
                CredentialsFixture(), transport
            ).execute(
                ReadPublicationPageInputDTO(
                    settings,
                    "root_group:100",
                    {
                        "version": 1,
                        "stage": "products",
                        "groups": [100],
                        "group_index": 0,
                        "last_id": None,
                    },
                )
            )
            self.assertEqual(get.await_args.kwargs["headers"]["X-LANGUAGE"], "ru")
            self.assertEqual(outcome.publications[0].core.title_locale, "ru")

    async def test_woocommerce_keys_are_sent_only_to_woocommerce_api(self) -> None:
        """Публичный WordPress root может отклонять Woo Basic, хотя ключи рабочие."""
        settings = ResourceSettingsDTO(
            "https://shop.example", {"locales": list(("uk",)), "currency": "UAH"}
        )
        transport = RepeatingTransport()

        async def response(
            path: str,
            *,
            query: dict[str, str] | None = None,
            headers: dict[str, str] | None = None,
        ) -> HttpResultDTO:
            """Разделяет публичный WordPress и защищённый WooCommerce endpoint."""
            if path == "/wp-json/":
                if headers and "Authorization" in headers:
                    raise PluginCallError("permission_denied")
                return HttpResultDTO({"url": "https://shop.example"}, {})
            self.assertEqual(path, "/wp-json/wc/v3/products")
            self.assertEqual(query, {"per_page": "1", "status": "any"})
            self.assertEqual(headers, {"Authorization": "Basic a2V5OnNlY3JldA=="})
            return HttpResultDTO([], {})

        with patch.object(transport, "get", AsyncMock(side_effect=response)) as get:
            outcome = await WooVerifyConnectionPlugin(
                CredentialsFixture(), transport
            ).execute(VerifyConnectionInputDTO(settings))
            self.assertEqual(outcome.identity, "site:https://shop.example")
            self.assertIsNone(outcome.reason_code)
            self.assertEqual(get.await_count, 2)

    async def test_woocommerce_public_root_does_not_verify_rejected_keys(self) -> None:
        """Доступность публичного WordPress не заменяет проверку прав на товары."""
        settings = ResourceSettingsDTO(
            "https://shop.example", {"locales": list(("uk",)), "currency": "UAH"}
        )
        transport = RepeatingTransport()
        with patch.object(
            transport,
            "get",
            AsyncMock(
                side_effect=[
                    HttpResultDTO({"url": "https://shop.example"}, {}),
                    PluginCallError("permission_denied"),
                ]
            ),
        ):
            with self.assertRaises(PluginCallError) as error:
                await WooVerifyConnectionPlugin(
                    CredentialsFixture(), transport
                ).execute(VerifyConnectionInputDTO(settings))
            self.assertEqual(error.exception.reason_code, "permission_denied")

    async def test_prom_verification_resolves_zero_scope_to_real_root(self) -> None:
        """Нулевой scope не становится общей identity разных магазинов."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
        )
        transport = RepeatingTransport()
        for root in (1000, 2000):
            with (
                self.subTest(root=root),
                patch.object(
                    transport,
                    "get",
                    AsyncMock(
                        side_effect=[
                            HttpResultDTO({"group_id": 0, "products": []}, {}),
                            HttpResultDTO(
                                {
                                    "groups": [
                                        {"id": root + 1, "parent_group_id": root},
                                        {"id": root, "parent_group_id": None},
                                    ]
                                },
                                {},
                            ),
                        ]
                    ),
                ) as get,
            ):
                outcome = await PromVerifyConnectionPlugin(
                    CredentialsFixture(), transport
                ).execute(VerifyConnectionInputDTO(settings))
                self.assertEqual(outcome.identity, f"root_group:{root}")
                self.assertIsNone(outcome.reason_code)
                self.assertEqual(outcome.limitations, ("api_visible_statuses_only",))
                self.assertEqual(get.await_count, 2)
                get.assert_awaited_with(
                    "/api/v1/groups/list",
                    query={"limit": "100"},
                    headers={"Authorization": "Bearer test"},
                )

    async def test_prom_verification_keeps_positive_root_identity(self) -> None:
        """Положительная identity ответа не требует дополнительных запросов."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
        )
        transport = RepeatingTransport()
        with patch.object(
            transport,
            "get",
            AsyncMock(
                return_value=HttpResultDTO({"group_id": 1000, "products": []}, {})
            ),
        ) as get:
            outcome = await PromVerifyConnectionPlugin(
                CredentialsFixture(), transport
            ).execute(VerifyConnectionInputDTO(settings))
            self.assertEqual(outcome.identity, "root_group:1000")
            get.assert_awaited_once_with(
                "/api/v1/products/list",
                query={"limit": "1"},
                headers={"Authorization": "Bearer test"},
            )

    async def test_prom_verification_rejects_invalid_root_group(self) -> None:
        """Разрешение нуля не принимает bool, строку, дробь и отсутствующий ID."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
        )
        transport = RepeatingTransport()
        for root in (-1, None, False, True, "0", 0.0):
            with (
                self.subTest(root=root),
                patch.object(
                    transport,
                    "get",
                    AsyncMock(
                        return_value=HttpResultDTO(
                            {"group_id": root, "products": []}, {}
                        )
                    ),
                ),
            ):
                with self.assertRaises(PluginCallError):
                    await PromVerifyConnectionPlugin(
                        CredentialsFixture(), transport
                    ).execute(VerifyConnectionInputDTO(settings))

    async def test_prom_zero_scope_requires_unambiguous_real_root(self) -> None:
        """Пустые, неоднозначные и повреждённые группы не подменяются нулём."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
        )
        transport = RepeatingTransport()
        for groups in (
            [],
            [{"id": 1000}],
            [
                {"id": 1000, "parent_group_id": None},
                {"id": 2000, "parent_group_id": None},
            ],
            [{"id": 0, "parent_group_id": None}],
            [{"id": False, "parent_group_id": None}],
            [None],
            [{"id": index, "parent_group_id": None} for index in range(1, 102)],
        ):
            with (
                self.subTest(groups=groups),
                patch.object(
                    transport,
                    "get",
                    AsyncMock(
                        side_effect=[
                            HttpResultDTO({"group_id": 0, "products": []}, {}),
                            HttpResultDTO({"groups": groups}, {}),
                        ]
                    ),
                ),
            ):
                with self.assertRaises(PluginCallError):
                    await PromVerifyConnectionPlugin(
                        CredentialsFixture(), transport
                    ).execute(VerifyConnectionInputDTO(settings))
        with self.assertRaises(PluginCallError):
            prom_normalize({"id": 0}, settings, observed_on=date(2026, 10, 18))

    async def test_repeating_woocommerce_page_is_rejected(self) -> None:
        """Плагин не маскирует повтор первой страницы увеличением номера."""
        settings = ResourceSettingsDTO(
            "https://shop.example", {"locales": list(("uk",)), "currency": "UAH"}
        )
        plugin = WooReadPublicationPagePlugin(
            CredentialsFixture(), RepeatingTransport()
        )
        first = await plugin.execute(
            ReadPublicationPageInputDTO(settings, "site:test", {})
        )
        with self.assertRaises(PluginCallError):
            await plugin.execute(
                ReadPublicationPageInputDTO(settings, "site:test", first.checkpoint)
            )

    async def test_repeating_prom_cursor_is_rejected(self) -> None:
        """Prom last_id монотонен и проверяется по возвращённым IDs."""
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
        )
        plugin = PromReadPublicationPagePlugin(
            CredentialsFixture(), RepeatingTransport()
        )
        first = await plugin.execute(
            ReadPublicationPageInputDTO(settings, "root_group:100", {})
        )
        with self.assertRaises(PluginCallError):
            await plugin.execute(
                ReadPublicationPageInputDTO(
                    settings, "root_group:100", first.checkpoint
                )
            )

    async def test_private_network_and_invalid_paths_are_rejected(self) -> None:
        """Scoped transport запрещает локальные адреса и смену origin через path."""
        with self.assertRaises(PluginCallError):
            await ScopedHttpTransport("https://127.0.0.1").get("/api")
        with self.assertRaises(PluginCallError):
            await ScopedHttpTransport("https://shop.example").get("//other.example/api")

    async def test_provider_cannot_expand_a_bounded_page(self) -> None:
        """Ответ сверх запрошенного лимита не превращается в долгую SQL-порцию."""
        settings = ResourceSettingsDTO(
            "https://shop.example", {"locales": list(("uk",)), "currency": "UAH"}
        )
        for plugin_type, body, identity in (
            (
                WooReadPublicationPagePlugin,
                [{"id": value} for value in range(1, 102)],
                "site:test",
            ),
            (
                PromReadPublicationPagePlugin,
                {"groups": [{"id": value} for value in range(1, 102)]},
                "root_group:1000",
            ),
        ):
            transport = RepeatingTransport()
            with patch.object(
                transport, "get", AsyncMock(return_value=HttpResultDTO(body, {}))
            ):
                with self.assertRaises(PluginCallError) as error:
                    await plugin_type(CredentialsFixture(), transport).execute(
                        ReadPublicationPageInputDTO(
                            (
                                ResourceSettingsDTO(
                                    "https://my.prom.ua",
                                    {"locales": ["ru"], "currency": "UAH"},
                                )
                                if identity.startswith("root_group:")
                                else settings
                            ),
                            identity,
                            {},
                        )
                    )
                self.assertEqual(
                    error.exception.reason_code, "page_size_limit_exceeded"
                )
