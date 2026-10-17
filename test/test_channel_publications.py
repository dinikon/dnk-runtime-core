"""Контракты внешнего чтения и идемпотентные шаги импорта публикаций."""

import json
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx

from src.modules.channels.application.publication_import_run.command.import_publication_page.command import (
    ImportPublicationPageCommand,
)
from src.modules.channels.application.publication_import_run.command.import_publication_page.handler import (
    ImportPublicationPageHandler,
)
from src.modules.channels.application.publication_import_run.command.prepare_publication_import.command import (
    PreparePublicationImportCommand,
)
from src.modules.channels.application.publication_import_run.command.prepare_publication_import.handler import (
    PreparePublicationImportHandler,
)
from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourceConnection,
    PublicationSourcePage,
)
from src.modules.channels.application.publication_import_run.service import (
    PublicationImportStarter,
)
from src.modules.channels.application.publication_import_run.worker_state import (
    PublicationImportState,
)
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.channel.value_object.kind import ChannelKind
from src.modules.channels.domain.channel.value_object.settings import ConnectionSettings
from src.modules.channels.domain.publication_import_run.aggregate import (
    PublicationImportRun,
)
from src.modules.channels.infrastructure.external_publication.content.html_sanitizer import (
    PublicationHtmlSanitizer,
)
from src.modules.channels.infrastructure.external_publication.persistence.mapper import (
    PublicationMapper,
)
from src.modules.channels.infrastructure.external_publication.persistence.document_mapper import (
    PublicationDocumentMapper,
)
from src.modules.channels.infrastructure.external_publication.persistence.query_mapper import (
    PublicationQueryMapper,
)
from src.modules.channels.presentation.external_publication.http.response.get_publication import (
    GetPublicationResponse,
)
from src.modules.channels.infrastructure.publication_import_run.source.normalizer import (
    PublicationNormalizer,
)
from src.modules.channels.infrastructure.publication_import_run.source.http_client import (
    PublicationJsonClient,
)
from src.modules.channels.infrastructure.publication_import_run.source.prom import (
    PromPublicationSource,
)
from src.modules.channels.infrastructure.publication_import_run.source.woocommerce import (
    WooPublicationSource,
)
from src.modules.channels.infrastructure.channel.definitions.registry import (
    CodeChannelRegistry,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class MemoryRuns:
    def __init__(self):
        self.values = {}

    async def get(self, id):
        return self.values.get(id)

    async def active(self, channel_id):
        return next(
            (
                run
                for run in self.values.values()
                if run.channel_id == channel_id and run.active
            ),
            None,
        )

    async def save(self, run):
        self.values[run.id] = run


class MemoryPublications:
    def __init__(self):
        self.values = {}

    async def find(self, channel_id, revision, resource_type, external_id):
        return self.values.get((channel_id, revision, resource_type, external_id))

    async def save(self, publication):
        self.values[
            (
                publication.channel_id,
                publication.connection_revision,
                publication.resource_type,
                publication.external_id,
            )
        ] = publication


class PublicationSourceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.normalizer = PublicationNormalizer(PublicationHtmlSanitizer())

    def test_prom_discount_from_native_payload_reaches_read_card_response(self):
        discount = {
            "type": "percent",
            "value": 20,
            "date_start": "07.10.2026",
            "date_end": "07.10.2026",
        }
        raw = {
            "id": 3222858785,
            "name": "Товар со скидкой",
            "price": 480.0,
            "currency": "UAH",
            "discount": discount,
        }
        resource = self.normalizer.normalize("prom", raw)
        stored = PublicationDocumentMapper.to_values(resource.document)
        self.assertEqual(
            PublicationDocumentMapper.to_document(stored), resource.document
        )
        dto = PublicationQueryMapper.to_details(
            {
                "id": uuid4(),
                "channel_id": uuid4(),
                "external_id": resource.external_id,
                "resource_type": "product",
                "revision": 1,
                "observed_at": datetime.now(UTC),
                "document": stored,
            },
            (),
        )
        response = GetPublicationResponse.from_dto(dto).model_dump(mode="json")
        self.assertEqual(Decimal(response["regular_price"]), Decimal("480"))
        self.assertEqual(Decimal(response["sale_price"]), Decimal("384"))
        self.assertEqual(Decimal(response["price"]), Decimal("480"))
        self.assertEqual(json.loads(resource.raw_payload)["discount"], discount)
        self.assertNotIn("raw_payload", response)
        self.assertEqual(resource.document.warnings, ())

    def test_prom_discount_amount_zero_and_invalid_values(self):
        for discount, price, expected in (
            ({"type": "amount", "value": "95.50"}, "480", "384.50"),
            ({"type": "percent", "value": 100}, "480", "0"),
            ({"type": "percent", "value": 0}, 0, "0"),
            ({"type": "percent", "value": -1}, "480", None),
            ({"type": "percent", "value": 101}, "480", None),
            ({"type": "amount", "value": 481}, "480", None),
            ({"type": "percent", "value": True}, "480", None),
            ({"type": "percent", "value": "NaN"}, "480", None),
            ({"type": "other", "value": 20}, "480", None),
            ({"type": "percent", "value": 20}, None, None),
            ("invalid", "480", None),
        ):
            with self.subTest(discount=discount, price=price):
                document = self.normalizer.normalize(
                    "prom",
                    {
                        "id": 1,
                        "name": "Товар",
                        "currency": "UAH",
                        "price": price,
                        "discount": discount,
                    },
                ).document
                self.assertEqual(
                    document.sale_price, None if expected is None else Decimal(expected)
                )
                self.assertEqual(
                    "invalid_discount" in document.warnings, expected is None
                )
        for discount in (None, {}):
            document = self.normalizer.normalize(
                "prom",
                {
                    "id": 1,
                    "name": "Товар",
                    "currency": "UAH",
                    "price": "480",
                    "discount": discount,
                },
            ).document
            self.assertEqual(document.regular_price, Decimal("480"))
            self.assertIsNone(document.sale_price)
            self.assertEqual(document.warnings, ())

    def test_woo_native_sale_prices_remain_independent_of_prom_discount(self):
        document = self.normalizer.normalize(
            "woocommerce",
            {
                "id": 1,
                "name": "Товар",
                "price": "384",
                "regular_price": "480",
                "sale_price": "384",
                "discount": {"type": "percent", "value": 50},
            },
            currency="UAH",
        ).document
        self.assertEqual(
            (document.price, document.regular_price, document.sale_price),
            (Decimal("384"), Decimal("480"), Decimal("384")),
        )

    async def test_prom_cursor_keeps_native_fields_zero_and_sanitized_description(self):
        requests = []

        def handle(request):
            requests.append(request)
            last = request.url.params.get("last_id")
            rows = (
                [
                    dict(
                        id=i,
                        name="Товар",
                        price=0,
                        quantity_in_stock=0,
                        currency="UAH",
                        description='<p>Описание</p><script>steal()</script><a href="javascript:bad()">Link</a>',
                        images=[{"url": "https://img.example/a.png"}],
                        native_extra={"unknown": True},
                    )
                    for i in range(200, 100, -1)
                ]
                if last is None
                else [dict(id=100, name="Last")]
            )
            return httpx.Response(200, json={"products": rows})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            source = PromPublicationSource(
                PublicationJsonClient(client), self.normalizer
            )
            connection = PublicationSourceConnection("prom", {}, {"api_key": "secret"})
            first = await source.read_page(connection, "{}")
            second = await source.read_page(connection, first.next_checkpoint)
        self.assertEqual(len(first.resources) + len(second.resources), 101)
        self.assertEqual(requests[1].url.params["last_id"], "100")
        self.assertIsNone(second.next_checkpoint)
        resource = first.resources[0]
        self.assertEqual(resource.document.price, Decimal(0))
        self.assertEqual(resource.document.quantity, Decimal(0))
        self.assertNotIn("script", resource.document.description_html)
        self.assertNotIn("javascript", resource.document.description_html)
        self.assertIn("Описание", resource.document.description_html)
        self.assertTrue(json.loads(resource.raw_payload)["native_extra"]["unknown"])
        self.assertTrue(all(request.method == "GET" for request in requests))
        self.assertEqual(requests[0].headers["Authorization"], "Bearer secret")
        self.assertNotIn("secret", repr(connection))

    async def test_woo_reads_all_variation_pages_before_next_product_page(self):
        seen = []

        def handle(request):
            path, page = request.url.path, int(request.url.params.get("page", 1))
            seen.append((path, page))
            if "settings" in path:
                return httpx.Response(200, json={"value": "EUR"})
            if path.endswith("/variations"):
                rows = [
                    dict(
                        id=i,
                        sku=f"v{i}",
                        price="12.40",
                        stock_quantity=0,
                        attributes=[{"name": "Цвет", "option": "Красный"}],
                    )
                    for i in (range(1001, 1101) if page == 1 else [1101])
                ]
                return httpx.Response(200, headers={"X-WP-TotalPages": "2"}, json=rows)
            rows = (
                [
                    dict(
                        id=10,
                        name="Variable",
                        type="variable",
                        variations=list(range(1001, 1102)),
                    )
                ]
                if page == 1
                else [dict(id=20, name="Simple", type="simple")]
            )
            return httpx.Response(200, headers={"X-WP-TotalPages": "2"}, json=rows)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            source = WooPublicationSource(
                PublicationJsonClient(client), self.normalizer
            )
            connection = PublicationSourceConnection(
                "woocommerce",
                {"url": "https://shop.example/store/"},
                {"consumer_key": "key", "consumer_secret": "secret"},
            )
            cursor, pages = "{}", []
            while cursor is not None:
                page = await source.read_page(connection, cursor)
                pages.append(page)
                cursor = page.next_checkpoint
        self.assertEqual([len(page.resources) for page in pages], [1, 100, 1, 1])
        self.assertEqual(pages[0].resources[0].document.expected_variations, 101)
        self.assertEqual(pages[1].resources[0].parent_external_id, "10")
        self.assertEqual(pages[1].resources[0].resource_type, "variation")
        self.assertEqual(pages[1].resources[0].document.currency, "EUR")
        self.assertEqual(pages[1].resources[0].document.quantity, Decimal(0))
        self.assertTrue(
            all(path.startswith("/store/wp-json/wc/v3/") for path, _ in seen)
        )
        self.assertEqual(sum("settings" in path for path, _ in seen), 1)

    async def test_currency_permission_failure_does_not_invent_currency_or_fail_products(
        self,
    ):
        def handle(request):
            if "settings" in request.url.path:
                return httpx.Response(403, json={"message": "secret response"})
            return httpx.Response(200, json=[{"id": 1, "price": "0", "name": "Free"}])

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await WooPublicationSource(
                PublicationJsonClient(client), self.normalizer
            ).read_page(
                PublicationSourceConnection(
                    "woocommerce",
                    {"url": "https://shop.example"},
                    {"consumer_key": "k", "consumer_secret": "s"},
                ),
                "{}",
            )
        self.assertIsNone(result.resources[0].document.currency)
        self.assertIn("currency_unavailable", result.resources[0].document.warnings)

    async def test_empty_prom_success_and_safe_retryable_errors(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"products": []})
            )
        ) as client:
            result = await PromPublicationSource(
                PublicationJsonClient(client), self.normalizer
            ).read_page(PublicationSourceConnection("prom", {}, {"api_key": "x"}), "{}")
        self.assertEqual(result, PublicationSourcePage((), None))
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(429, text="sensitive upstream response")
            )
        ) as client:
            with self.assertRaises(PublicationSourceError) as raised:
                await PublicationJsonClient(client).get(
                    "https://example.com", headers={}, params={}
                )
        self.assertTrue(raised.exception.retryable)
        self.assertEqual(str(raised.exception), "source_unavailable")

    async def test_repeated_source_pages_fail_instead_of_completing_or_looping(self):
        cases = (
            (
                "prom",
                '{"last_id": 99}',
                {"products": [{"id": 100, "name": "Repeated"}]},
            ),
            (
                "woocommerce",
                '{"currency": "UAH", "page": 2, "last_product_id": 100}',
                [{"id": 100, "name": "Repeated"}],
            ),
            ("woocommerce", '{"currency": "UAH", "page": 2}', []),
        )
        for kind, checkpoint, payload in cases:
            with self.subTest(kind=kind, checkpoint=checkpoint):
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(
                        lambda request: httpx.Response(
                            200, headers={"X-WP-TotalPages": "3"}, json=payload
                        )
                    )
                ) as client:
                    source = (
                        PromPublicationSource(
                            PublicationJsonClient(client), self.normalizer
                        )
                        if kind == "prom"
                        else WooPublicationSource(
                            PublicationJsonClient(client), self.normalizer
                        )
                    )
                    with self.assertRaises(PublicationSourceError) as raised:
                        await source.read_page(
                            PublicationSourceConnection(
                                kind,
                                {"url": "https://shop.example"},
                                {
                                    "api_key": "x",
                                    "consumer_key": "k",
                                    "consumer_secret": "s",
                                },
                            ),
                            checkpoint,
                        )
                self.assertEqual(raised.exception.code, "pagination_stalled")

    async def test_prom_relations_only_use_explicit_base_ids_and_safe_urls(self):
        resource = self.normalizer.normalize(
            "prom",
            {
                "id": 20,
                "name": "Same",
                "sku": "Same",
                "is_variation": True,
                "variation_base_id": 10,
                "url": "javascript:bad()",
                "main_image": "https://user:pass@img.example/a",
            },
        )
        self.assertEqual(resource.parent_external_id, "10")
        self.assertEqual(resource.resource_type, "product")
        self.assertIsNone(resource.document.external_url)
        self.assertEqual(resource.document.images, ())
        other = self.normalizer.normalize(
            "prom", {"id": 21, "name": "Same", "sku": "Same"}
        )
        self.assertIsNone(other.parent_external_id)


class PublicationImportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 7, tzinfo=UTC)
        self.tenant = uuid4()
        self.channel = Channel.create(
            channel_id=ChannelIdVO.from_value(uuid4()),
            name="Store",
            kind=ChannelKind.PROM,
            config_version=1,
            settings=ConnectionSettings({}, "sealed", ("api_key",)),
            actor_id=EntityIdVO.from_value(uuid4()),
            now=self.now,
        )
        self.channels = Mock(
            get_for_update=AsyncMock(side_effect=lambda id: self.channel)
        )
        self.runs, self.publications = MemoryRuns(), MemoryPublications()
        self.jobs = Mock(
            schedule_once=AsyncMock(return_value=True),
            owns_current_lease=AsyncMock(return_value=True),
            terminal_or_missing=AsyncMock(return_value=set()),
        )
        self.clock, self.uuids = Mock(now=Mock(return_value=self.now)), Mock(
            new=Mock(side_effect=uuid4)
        )
        self.state = PublicationImportState(
            self.channels, self.runs, self.jobs, self.clock
        )
        self.normalizer = PublicationNormalizer(PublicationHtmlSanitizer())
        self.starter = PublicationImportStarter(
            self.runs, self.jobs, self.uuids, CodeChannelRegistry()
        )

    async def start(self):
        return await self.starter.start(
            channel=self.channel, tenant_id=self.tenant, now=self.now
        )

    def args(self, run):
        return dict(
            tenant_id=self.tenant,
            channel_id=self.channel.id.uuid,
            run_id=run.id.uuid,
            job_id=run.job_id.uuid,
            lock_token="lease",
        )

    async def test_repeated_start_reuses_active_run_and_empty_import_succeeds(self):
        run = await self.start()
        repeated = await self.start()
        self.assertEqual(run.id, repeated.id)
        self.jobs.schedule_once.assert_awaited_once()
        result = await ImportPublicationPageHandler(
            self.state, self.publications, self.uuids
        ).execute(
            ImportPublicationPageCommand(
                **self.args(run), page=PublicationSourcePage((), None), expected_pages=0
            )
        )
        self.assertTrue(result.completed)
        self.assertEqual(self.runs.values[run.id].status, "succeeded")
        self.assertEqual(self.runs.values[run.id].resources, 0)

    async def test_page_checkpoint_replay_and_repeat_import_keep_ids_and_revisions(
        self,
    ):
        run = await self.start()
        resource = self.normalizer.normalize(
            "prom", {"id": 1, "name": "Товар", "price": 0, "currency": "UAH"}
        )
        handler = ImportPublicationPageHandler(
            self.state, self.publications, self.uuids
        )
        command = ImportPublicationPageCommand(
            **self.args(run),
            page=PublicationSourcePage((resource,), '{"last_id": 1}'),
            expected_pages=0,
        )
        self.assertTrue((await handler.execute(command)).saved)
        self.assertFalse((await handler.execute(command)).saved)
        current = self.runs.values[run.id]
        self.assertEqual(current.pages, 1)
        self.assertEqual(current.resources, 1)
        self.assertEqual(current.checkpoint, '{"last_id": 1}')
        original = next(iter(self.publications.values.values()))
        roundtrip = PublicationMapper.to_domain(PublicationMapper.to_values(original))
        self.assertEqual(roundtrip, original)
        await handler.execute(
            ImportPublicationPageCommand(
                **self.args(current),
                page=PublicationSourcePage((), None),
                expected_pages=1,
            )
        )
        second = await self.start()
        await handler.execute(
            ImportPublicationPageCommand(
                **self.args(second),
                page=PublicationSourcePage((resource,), None),
                expected_pages=0,
            )
        )
        updated = next(iter(self.publications.values.values()))
        self.assertEqual(updated.id, original.id)
        self.assertEqual(updated.revision, 1)
        self.assertEqual(len(self.publications.values), 1)

    async def test_changed_settings_and_lost_lease_cannot_save_stale_source_page(self):
        run = await self.start()
        prepared = await PreparePublicationImportHandler(
            self.state, Mock(decrypt=Mock(return_value={"api_key": "secret"}))
        ).execute(PreparePublicationImportCommand(**self.args(run)))
        self.assertEqual(prepared.connection.secrets, {"api_key": "secret"})
        self.channel = self.channel.change_settings(
            ConnectionSettings({}, "new-sealed", ("api_key",)),
            1,
            actor_id=self.channel.updated_by,
            now=self.now,
        )
        self.assertEqual(self.channel.connection_revision, 2)
        resource = self.normalizer.normalize("prom", {"id": 1})
        result = await ImportPublicationPageHandler(
            self.state, self.publications, self.uuids
        ).execute(
            ImportPublicationPageCommand(
                **self.args(run),
                page=PublicationSourcePage((resource,), None),
                expected_pages=0,
            )
        )
        self.assertFalse(result.saved)
        self.assertEqual(self.publications.values, {})
        self.assertEqual(self.runs.values[run.id].status, "failed")
        self.assertEqual(self.runs.values[run.id].error_code, "connection_changed")
        second = await self.start()
        self.jobs.owns_current_lease.return_value = False
        result = await ImportPublicationPageHandler(
            self.state, self.publications, self.uuids
        ).execute(
            ImportPublicationPageCommand(
                **self.args(second),
                page=PublicationSourcePage((resource,), None),
                expected_pages=0,
            )
        )
        self.assertFalse(result.saved)
        self.assertEqual(self.publications.values, {})

    async def test_partial_failure_and_exhausted_job_can_restart_without_losing_data(
        self,
    ):
        run = await self.start()
        resource = self.normalizer.normalize("prom", {"id": 1})
        await ImportPublicationPageHandler(
            self.state, self.publications, self.uuids
        ).execute(
            ImportPublicationPageCommand(
                **self.args(run),
                page=PublicationSourcePage((resource,), '{"last_id":1}'),
                expected_pages=0,
            )
        )
        current = self.runs.values[run.id]
        self.jobs.terminal_or_missing.return_value = {current.job_id.uuid}
        second = await self.start()
        self.assertNotEqual(second.id, run.id)
        self.assertEqual(self.runs.values[run.id].status, "partial")
        self.assertEqual(len(self.publications.values), 1)


if __name__ == "__main__":
    unittest.main()
