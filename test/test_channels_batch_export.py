"""Инварианты пакетного экспорта, календаря, подписанного файла и XML-контракта."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
import unittest
from uuid import uuid4
from defusedxml.ElementTree import fromstring
from src.modules.channels.domain.batch_export.aggregate import BatchExportRun, ACTIVE
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO
from src.modules.channels.domain.export_schedule.aggregate import ExportSchedule
from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.domain.content_update.value_object.texts import (
    ContentTextsVO,
    LocalizedTextVO,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsNotFoundError,
    ChannelsValidationError,
)
from src.modules.channels.infrastructure.batch_export.feed_links import ExportFeedLinks
from src.modules.channels.infrastructure.plugin.prom.batch_export import (
    PromBatchExportPlugin,
)
from src.modules.channels.infrastructure.http.transport import ScopedHttpTransport
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class BatchExportDomainTests(unittest.TestCase):
    """Проверяет значимые ограничения, включая потерянный ответ записи и DST."""

    def test_default_export_permission_and_unbind_reset(self) -> None:
        """Связывание не включает экспорт; снятие связи сбрасывает явное разрешение."""
        rep = ProductRepresentation.create(
            EntityIdVO(uuid4()), EntityIdVO(uuid4()), EntityIdVO(uuid4())
        )
        actor, binding = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        rep.bind(
            binding,
            EntityIdVO(uuid4()),
            rep.connection_id,
            rep.revision,
            actor,
            datetime.now(UTC),
        )
        self.assertFalse(rep.export_enabled)
        rep.set_export(True, rep.revision)
        rep.unbind(binding, rep.revision, actor, datetime.now(UTC))
        self.assertFalse(rep.export_enabled)
        with self.assertRaises(ChannelsConflictError):
            rep.set_export(True, rep.revision)

    def test_submission_recovery_cannot_claim_again(self) -> None:
        """Неопределённая запись допускает проверку, не возврат к отправке."""
        now = datetime.now(UTC)
        run = BatchExportRun.create(uuid4(), uuid4(), uuid4(), None, 1, "daily", now)
        run.advance("preparing", "checking", now)
        run.advance("checking", "building", now)
        run.artifact_ready("a" * 64, 123, now)
        run.claim_submission(now)
        run.fail("network_error", now, uncertain=True)
        run.reconcile(now)
        self.assertEqual(run.status, "verifying")
        with self.assertRaises(ChannelsConflictError):
            run.claim_submission(now)

    def test_calendar_dst_and_no_backlog(self) -> None:
        """Пропущенный час нормализуется, повторный час не запускает второй пакет."""
        schedule = ExportSchedule.create(uuid4())
        schedule.change(
            True, 3, 30, "Europe/Kyiv", 1, datetime(2026, 3, 28, 15, tzinfo=UTC)
        )
        self.assertEqual(schedule.next_at, datetime(2026, 3, 29, 1, 30, tzinfo=UTC))
        after_fold = datetime(2026, 10, 25, 1, 5, tzinfo=UTC)
        self.assertEqual(
            schedule.next_after(after_fold), datetime(2026, 10, 26, 1, 30, tzinfo=UTC)
        )
        schedule.consumed(datetime(2026, 11, 1, 15, tzinfo=UTC))
        self.assertEqual(schedule.next_at, datetime(2026, 11, 2, 1, 30, tzinfo=UTC))

    def test_invalid_policy_and_stale_revision(self) -> None:
        """Не принимает произвольную зону и не перезаписывает новую policy устаревшей формой."""
        schedule = ExportSchedule.create(uuid4())
        with self.assertRaises(ChannelsValidationError):
            schedule.change(True, 3, 0, "Not/AZone", 1, datetime.now(UTC))
        with self.assertRaises(ChannelsConflictError):
            schedule.change(False, 3, 0, "UTC", 2, datetime.now(UTC))

    def test_feed_signature_cannot_move_between_runs_tenants_or_expiry(self) -> None:
        """Capability не даёт доступа к другому файлу и истекает независимо от сессии."""
        links = ExportFeedLinks("private-test-key")
        tenant, run = uuid4(), uuid4()
        now = datetime.now(UTC)
        expires = now + timedelta(hours=1)
        token = links.token(tenant, run, expires)
        self.assertEqual(links.authorize(run, token, now), tenant)
        for identifier, value, at in [
            (uuid4(), token, now),
            (run, token.replace(tenant.hex, uuid4().hex), now),
            (run, token, expires + timedelta(seconds=1)),
        ]:
            with self.assertRaises(ChannelsNotFoundError):
                links.authorize(identifier, value, at)
        with self.assertRaises(ChannelsNotFoundError):
            ExportFeedLinks("").authorize(run, token, now)

    def test_tenant_origins_and_file_only_state_prevent_submission(self) -> None:
        """Домен tenant задаёт адрес; локальный файл завершает слот без разрешения POST."""
        links = ExportFeedLinks("test-signing-key")
        tenant, run_id = uuid4(), uuid4()
        now = datetime.now(UTC)
        self.assertTrue(
            links.url("localhost", tenant, run_id, now).startswith(
                "http://localhost/api/"
            )
        )
        self.assertTrue(
            links.url("shop.example", tenant, run_id, now).startswith(
                "https://shop.example/api/"
            )
        )
        for host in (
            "evil.example/path",
            "https://example.com",
            "user@example.com",
            "localhost:8000",
            "10.0.0.1",
            "",
        ):
            self.assertEqual(links.origin(host), "")
        run = BatchExportRun.create(
            run_id, uuid4(), uuid4(), None, 1, "manual", now, delivery_mode="file"
        )
        run.advance("preparing", "checking", now)
        run.advance("checking", "building", now)
        run.artifact_ready("a" * 64, 20, now)
        with self.assertRaises(ChannelsConflictError):
            run.claim_submission(now)
        run.complete_file(now)
        self.assertEqual(run.status, "prepared")
        self.assertNotIn(run.status, ACTIVE)

    def test_xml_is_minimal_and_escapes_both_locales_and_identity(self) -> None:
        """Файл явно сохраняет категорию и не передаёт цену, остатки, SKU или группу."""
        item = ExportItemVO(
            uuid4(),
            uuid4(),
            uuid4(),
            1,
            uuid4(),
            "123",
            {},
            ContentTextsVO(
                (
                    LocalizedTextVO("ru", "RU & <name>", "<p>RU & ]]> body</p>"),
                    LocalizedTextVO("uk", "UK", "<p>UK</p>"),
                )
            ),
            {"category": {"id": 1333}},
            "ready",
            (),
            'key-"&',
        )
        plugin = PromBatchExportPlugin(None, None)
        stream = BytesIO()
        plugin.begin(stream)
        plugin.append(stream, item)
        plugin.end(stream)
        xml = fromstring(stream.getvalue())
        offer = xml.find("./shop/offers/offer")
        self.assertEqual(offer.attrib, {"id": 'key-"&'})
        self.assertEqual(
            {child.tag for child in offer},
            {"name", "description", "name_ua", "description_ua", "portal_category_id"},
        )
        self.assertEqual(offer.findtext("description"), "<p>RU & ]]> body</p>")
        self.assertEqual(offer.findtext("portal_category_id"), "1333")
        bad = replace(
            item, desired=ContentTextsVO((LocalizedTextVO("ru", "Bad\x01", "body"),))
        )
        with self.assertRaises(PluginCallError):
            plugin.append(BytesIO(), bad)


class ExportTransportTests(unittest.IsolatedAsyncioTestCase):
    """Общий HTTP ограничивает область и размер, контракт площадки остаётся в плагине."""

    async def test_rejects_invalid_or_oversized_json_before_network(self) -> None:
        """Не допускает произвольный объект или неограниченную нагрузку в shared transport."""
        transport = ScopedHttpTransport("https://source.example")
        for payload in (
            {"bad": object()},
            {"text": "x" * (1024 * 1024 + 1)},
            {"number": float("nan")},
        ):
            with self.assertRaises(PluginCallError):
                await transport.post("/api/submit", payload=payload)

    async def test_prom_plugin_owns_closed_text_import_contract(self) -> None:
        """Ни общий transport, ни каталог не задают поля обновления или правила отсутствующих карточек."""
        from src.modules.channels.application.plugin_contract import (
            ResourceSettingsDTO,
            HttpResultDTO,
            ConnectionCredentialsDTO,
        )

        class Credentials:
            """Возвращает только фиктивные scoped credentials."""

            async def resolve(self) -> ConnectionCredentialsDTO:
                """Выдаёт тестовый token без обращения к хранилищу."""
                return ConnectionCredentialsDTO({"token": "fixture"})

        class Http:
            """Фиксирует request плагина без сети и provider условий в транспорте."""

            def __init__(self) -> None:
                """Готовит хранилище одного проверяемого запроса."""
                self.sent = None

            async def post(
                self,
                path: str,
                *,
                payload: dict[str, object],
                headers: dict[str, str] | None = None,
            ) -> HttpResultDTO:
                """Возвращает непрозрачный внешний import ID."""
                self.sent = (path, payload)
                return HttpResultDTO({"status": "success", "id": "fixture-id"}, {})

        http = Http()
        plugin = PromBatchExportPlugin(Credentials(), http)
        settings = ResourceSettingsDTO(
            "https://my.prom.ua", {"locales": ["ru", "uk"], "currency": "UAH"}
        )
        await plugin.submit(settings, "https://runtime.example/api/channels/file.xml")
        self.assertEqual(
            http.sent,
            (
                "/api/v1/products/import_url",
                {
                    "url": "https://runtime.example/api/channels/file.xml",
                    "force_update": True,
                    "only_available": False,
                    "mark_missing_product_as": "none",
                    "updated_fields": [
                        "name",
                        "description",
                        "name_ua",
                        "description_ua",
                    ],
                },
            ),
        )
        for url in (
            "http://runtime.example/file.xml",
            "https://user:password@runtime.example/file.xml",
        ):
            with self.assertRaises(PluginCallError):
                await plugin.submit(settings, url)
