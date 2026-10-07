"""Контракты авторизации, полного обхода и Read-карточки Rozetka без живых credentials."""

import asyncio
import base64
import json
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
import httpx
from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
    PublicationImportUnavailableError,
)
from src.modules.channels.application.publication_import_run.service import (
    PublicationImportStarter,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourceConnection,
)
from src.modules.channels.domain.channel.value_object.kind import ChannelKind
from src.modules.channels.infrastructure.channel.definitions.registry import (
    CodeChannelRegistry,
)
from src.modules.channels.infrastructure.channel.validation.connection import (
    JsonSchemaConnectionValidator,
)
from src.modules.channels.infrastructure.external_publication.content.html_sanitizer import (
    PublicationHtmlSanitizer,
)
from src.modules.channels.infrastructure.external_publication.persistence.document_mapper import (
    PublicationDocumentMapper,
)
from src.modules.channels.infrastructure.external_publication.persistence.query_mapper import (
    PublicationQueryMapper,
)
from src.modules.channels.infrastructure.publication_import_run.source.http_client import (
    PublicationJsonClient,
)
from src.modules.channels.infrastructure.publication_import_run.source.normalizer import (
    PublicationNormalizer,
)
from src.modules.channels.infrastructure.publication_import_run.source.rozetka import (
    RozetkaPublicationSource,
    cursor_from,
    detail_item,
    list_page,
)
from src.modules.channels.infrastructure.publication_import_run.source.rozetka_auth import (
    content,
)
from src.modules.channels.infrastructure.publication_import_run.source.rozetka_normalizer import (
    RozetkaPublicationNormalizer,
)
from src.modules.channels.presentation.external_publication.http.response.get_publication import (
    GetPublicationResponse,
)
from test.rozetka_support import read_fixture, RozetkaFixtureApi
from test import test_channel_publications as publication_tests


class RozetkaSourceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.normalizer = RozetkaPublicationNormalizer(PublicationHtmlSanitizer())
        self.connection = PublicationSourceConnection(
            "rozetka", {"username": "fixture-user"}, {"password": "пароль-secret"}
        )

    async def test_list_details_multiple_sources_archive_and_bounded_resume(self):
        api = RozetkaFixtureApi()
        resources, checkpoints = [], []
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(api.handle)
        ) as client:
            source = RozetkaPublicationSource(
                PublicationJsonClient(client), self.normalizer
            )
            checkpoint = "{}"
            for _ in range(20):
                before = len(api.requests)
                page = await source.read_page(self.connection, checkpoint)
                self.assertLessEqual(len(page.resources), 1)
                self.assertLessEqual(len(api.requests) - before, 3)
                resources.extend(page.resources)
                if page.next_checkpoint is None:
                    break
                checkpoint = page.next_checkpoint
                checkpoints.append(checkpoint)
            else:
                self.fail("Source did not terminate")
        self.assertEqual(
            [r.external_id for r in resources], ["11", "12", "13", "14", "13", "15"]
        )
        lists = [
            r for r in api.requests if r.url.path in ("/goods/all", "/goods/archive")
        ]
        self.assertEqual(len(lists), 5)
        self.assertEqual(
            [r.url.params.get("available") for r in lists], ["0", "1", "1", "2", None]
        )
        for request in api.requests:
            if request.url.path == "/sites":
                payload = json.loads(request.content)
                self.assertEqual(
                    payload,
                    {
                        "username": "fixture-user",
                        "password": base64.b64encode("пароль-secret".encode()).decode(),
                    },
                )
            if request.url.path == "/goods/details":
                self.assertIn("sync_source_id", request.url.params)
        native = json.dumps([r.raw_payload for r in resources] + checkpoints)
        for secret in ("пароль-secret", "fixture-user", "fixture-token"):
            self.assertNotIn(secret, native)
        self.assertTrue(any(json.loads(cp)["pending"] for cp in checkpoints))

    async def test_empty_account_finishes_after_all_streams_without_details(self):
        api = RozetkaFixtureApi()

        def handle(request):
            if request.method == "POST":
                return api.handle(request)
            self.assertNotEqual(request.url.path, "/goods/details")
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "content": {
                        "items": [],
                        "_meta": {
                            "currentPage": 1,
                            "pageCount": 0,
                            "perPage": 20,
                            "totalCount": 0,
                        },
                    },
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            source = RozetkaPublicationSource(
                PublicationJsonClient(client), self.normalizer
            )
            checkpoint = "{}"
            for index in range(4):
                page = await source.read_page(self.connection, checkpoint)
                self.assertEqual(page.resources, ())
                self.assertEqual(page.next_checkpoint is None, index == 3)
                checkpoint = page.next_checkpoint

    def test_native_fields_discount_false_zero_and_html_reach_http_card(self):
        fixture = read_fixture()
        resource = self.normalizer.normalize(
            fixture["list_item"], fixture["detail_item"]
        )
        document = resource.document
        self.assertEqual(
            (document.price, document.regular_price, document.sale_price),
            (Decimal(999), Decimal(1200), Decimal(777)),
        )
        self.assertEqual(document.quantity, Decimal(0))
        self.assertIsNone(document.currency)
        self.assertEqual(document.warnings, ("currency_unavailable",))
        self.assertEqual(document.source_status, "Новий (0)")
        self.assertEqual(
            [v.value for v in document.attributes], ["XS, XL", "Нет", "0", "значення"]
        )
        self.assertEqual(len(document.categories), 1)
        self.assertEqual(
            [image.url for image in document.images],
            ["https://content.example/phone.jpg"],
        )
        self.assertNotIn("script", document.description_html)
        self.assertIsNone(resource.parent_external_id)
        self.assertEqual(json.loads(resource.raw_payload), fixture)
        stored = PublicationDocumentMapper.to_values(document)
        self.assertEqual(PublicationDocumentMapper.to_document(stored), document)
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
        self.assertEqual(response["sale_price"], "777")
        self.assertEqual(response["attributes"][1]["value"], "Нет")
        self.assertNotIn("raw_payload", response)

    def test_price_zero_sentinels_typed_prices_and_nullable_images(self):
        cases = [
            ({"price": 0, "price_old": 0, "price_promo": 0}, ("0", "0", None)),
            (
                {"price": 999, "price_old": 1200, "price_promo": 0},
                ("999", "1200", "999"),
            ),
            ({"price": 999, "price_old": 0, "price_promo": 777}, ("999", "999", "777")),
            (
                {"price": 999, "price_old": 100, "price_promo": 999},
                ("999", "999", None),
            ),
            (
                {
                    "price": None,
                    "prices": [
                        {"price_type": 2, "price": "999.50"},
                        {"price_type": 1, "price": 1200},
                    ],
                },
                ("999.50", "1200", "999.50"),
            ),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                document = self.normalizer.normalize(
                    {"item_id": 1},
                    {
                        "item_id": 1,
                        "photo": None,
                        "photo_preview": "https://content.example/preview.jpg",
                        **raw,
                    },
                ).document
                self.assertEqual(
                    tuple(
                        None if value is None else str(value)
                        for value in (
                            document.price,
                            document.regular_price,
                            document.sale_price,
                        )
                    ),
                    expected,
                )
                self.assertEqual(len(document.images), 1)
        self.assertEqual(
            self.normalizer.normalize(
                {"item_id": 1},
                {"item_id": 1, "photo": ["javascript:bad"], "photo_preview": None},
            ).document.images,
            (),
        )

    def test_invalid_optional_prices_warn_without_creating_false_discount(self):
        for values in (
            {"price": -1, "price_old": -2, "price_promo": False},
            {"price": "NaN", "price_old": "bad", "price_promo": True},
        ):
            with self.subTest(values=values):
                document = self.normalizer.normalize(
                    {"item_id": 1}, {"item_id": 1, **values}
                ).document
                self.assertIsNone(document.price)
                self.assertIsNone(document.sale_price)
                self.assertIn("invalid_price", document.warnings)
                self.assertIn("invalid_discount", document.warnings)

    async def test_expired_token_is_renewed_once_without_retrying_permission_denial(
        self,
    ):
        api = RozetkaFixtureApi()
        gets = 0

        def handle(request):
            nonlocal gets
            if request.method == "GET":
                gets += 1
                if gets == 1:
                    return httpx.Response(
                        200,
                        json={
                            "success": False,
                            "errors": {"code": 6001, "message": "session_expired"},
                        },
                    )
            return api.handle(request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            page = await RozetkaPublicationSource(
                PublicationJsonClient(client), self.normalizer
            ).read_page(self.connection, "{}")
            self.assertEqual(api.logins, 2)
            self.assertIsNotNone(page.next_checkpoint)
        for failure, logins in ((6001, 2), (1010, 1)):
            api = RozetkaFixtureApi()

            def reject(request):
                return (
                    api.handle(request)
                    if request.method == "POST"
                    else httpx.Response(
                        200, json={"success": False, "errors": {"code": failure}}
                    )
                )

            async with httpx.AsyncClient(
                transport=httpx.MockTransport(reject)
            ) as client:
                with self.assertRaises(PublicationSourceError) as caught:
                    await RozetkaPublicationSource(
                        PublicationJsonClient(client), self.normalizer
                    ).read_page(self.connection, "{}")
            self.assertEqual(caught.exception.code, "access_denied")
            self.assertEqual(api.logins, logins)

    async def test_auth_and_transport_errors_are_safe_and_classified(self):
        for http_status, body, code, retryable in (
            (
                200,
                {
                    "success": False,
                    "errors": {"code": 1004, "message": "пароль-secret"},
                },
                "access_denied",
                False,
            ),
            (
                200,
                {"success": False, "errors": {"code": 0}},
                "source_unavailable",
                True,
            ),
            (429, {}, "source_unavailable", True),
            (503, {}, "source_unavailable", True),
            (403, {}, "access_denied", False),
            (
                200,
                {"success": True, "content": {"access_token": []}},
                "invalid_source_data",
                False,
            ),
            (200, {"success": "true", "content": {}}, "invalid_source_data", False),
        ):
            with self.subTest(status=http_status, body=body):
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(
                        lambda r: httpx.Response(http_status, json=body)
                    )
                ) as client:
                    with self.assertRaises(PublicationSourceError) as caught:
                        await RozetkaPublicationSource(
                            PublicationJsonClient(client), self.normalizer
                        ).read_page(self.connection, "{}")
                self.assertEqual(
                    (caught.exception.code, caught.exception.retryable),
                    (code, retryable),
                )
                self.assertNotIn("пароль-secret", str(caught.exception))
        with self.assertRaises(PublicationSourceError) as caught:
            content({"success": False, "errors": {"code": 1019}})
        self.assertEqual(caught.exception.code, "source_item_not_found")

    async def test_total_budget_timeout_and_post_allowlist_body_size_and_redirects(
        self,
    ):
        async def slow(request):
            await asyncio.sleep(0.1)
            return httpx.Response(200, json={})

        async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
            with self.assertRaises(PublicationSourceError) as caught:
                await RozetkaPublicationSource(
                    PublicationJsonClient(client), self.normalizer, budget_seconds=0.001
                ).read_page(self.connection, "{}")
            self.assertTrue(caught.exception.retryable)
        for status, code in (
            (200, "source_response_too_large"),
            (302, "source_request_rejected"),
        ):
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(
                        status,
                        content=b"x" * 20,
                        headers={"Location": "https://bad.example"},
                    )
                ),
                follow_redirects=True,
            ) as client:
                json_client = PublicationJsonClient(client, max_bytes=10)
                with self.assertRaises(PublicationSourceError) as caught:
                    await json_client.post(
                        "https://api-seller.rozetka.com.ua/sites",
                        headers={},
                        payload={"password": "secret"},
                    )
                self.assertEqual(caught.exception.code, code)
                with self.assertRaises(PublicationSourceError) as caught:
                    await json_client.post(
                        "https://bad.example/sites", headers={}, payload={}
                    )
                self.assertEqual(caught.exception.code, "invalid_source_url")

    def test_invalid_identity_details_cursor_and_stalled_pages_fail_closed(self):
        self.assertEqual(detail_item({"item": {"item_id": 1}}, 1), {"item_id": 1})
        for value in (
            [{"item_id": 2}],
            [{"item_id": 1}, {"item_id": 2}],
            [],
            {"item_id": None},
            {"item_id": True},
        ):
            with self.assertRaises(PublicationSourceError):
                detail_item({"item": value}, 1)
        valid = {
            "items": [{"item_id": 1}],
            "_meta": {"currentPage": 1, "perPage": 20, "totalCount": 1, "pageCount": 1},
        }
        _, _, fingerprint = list_page(valid, 1, [])
        for value, page, recent in (
            (valid, 2, []),
            (valid, 1, [fingerprint]),
            (
                {**valid, "items": [], "_meta": {**valid["_meta"], "pageCount": 2}},
                1,
                [],
            ),
            ({**valid, "items": [{"item_id": 1}, {"item_id": 1}]}, 1, []),
        ):
            with self.assertRaises(PublicationSourceError):
                list_page(value, page, recent)
        for cp in (
            "null",
            "[]",
            "bad",
            '{"token":"secret"}',
            json.dumps({**cursor_from("{}"), "stream": 4}),
        ):
            with self.assertRaises(PublicationSourceError):
                cursor_from(cp)
        with self.assertRaises(PublicationSourceError):
            PublicationNormalizer(PublicationHtmlSanitizer()).normalize(
                "rozetka", {"id": 1}
            )

    def test_connection_schema_is_text_and_password_not_url(self):
        definition = CodeChannelRegistry().get("rozetka")
        self.assertTrue(definition.reads_publications)
        self.assertEqual(
            definition.config["connection"]["ui_schema"][0]["widget"], "text"
        )
        self.assertNotIn(
            "format",
            definition.config["connection"]["json_schema"]["properties"]["username"],
        )
        self.assertTrue(
            definition.config["connection"]["json_schema"]["properties"]["password"][
                "writeOnly"
            ]
        )
        JsonSchemaConnectionValidator().validate(
            definition, {"username": "seller", "password": "secret"}
        )

    async def test_post_pins_public_dns_tls_host_and_rejects_private_resolution(self):
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, json={"success": True, "content": {}})

        for address, allowed in (
            ("1.1.1.1", True),
            ("127.0.0.1", False),
            ("10.0.0.1", False),
        ):
            client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
            with (
                patch(
                    "asyncio.BaseEventLoop.getaddrinfo",
                    new=AsyncMock(return_value=[(2, 1, 6, "", (address, 443))]),
                ),
                patch(
                    "src.modules.channels.infrastructure.publication_import_run.source.http_client.httpx.AsyncClient",
                    return_value=client,
                ) as factory,
            ):
                adapter = PublicationJsonClient(timeout=10)
                if allowed:
                    await adapter.post(
                        "https://api-seller.rozetka.com.ua/sites",
                        headers={},
                        payload={"password": "secret"},
                    )
                    factory.assert_called_once_with(
                        timeout=10, follow_redirects=False, trust_env=False
                    )
                    self.assertEqual(requests[-1].url.host, address)
                    self.assertEqual(
                        requests[-1].headers["Host"], "api-seller.rozetka.com.ua"
                    )
                    self.assertEqual(
                        requests[-1].extensions["sni_hostname"],
                        "api-seller.rozetka.com.ua",
                    )
                else:
                    with self.assertRaises(PublicationSourceError) as caught:
                        await adapter.post(
                            "https://api-seller.rozetka.com.ua/sites",
                            headers={},
                            payload={},
                        )
                    self.assertEqual(caught.exception.code, "invalid_source_url")
                    factory.assert_not_called()
            await client.aclose()

    async def test_http_unauthorized_renews_but_transport_error_remains_safe(self):
        api = RozetkaFixtureApi()
        gets = 0

        def handle(request):
            nonlocal gets
            if request.method == "GET":
                gets += 1
                if gets == 1:
                    return httpx.Response(401)
            return api.handle(request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            await RozetkaPublicationSource(
                PublicationJsonClient(client), self.normalizer
            ).read_page(self.connection, "{}")
        self.assertEqual(api.logins, 2)

        def fail(request):
            raise httpx.ConnectError("пароль-secret", request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
            with self.assertRaises(PublicationSourceError) as caught:
                await RozetkaPublicationSource(
                    PublicationJsonClient(client), self.normalizer
                ).read_page(self.connection, "{}")
            self.assertEqual(caught.exception.code, "source_unavailable")
            self.assertTrue(caught.exception.retryable)
            self.assertNotIn("пароль-secret", str(caught.exception))


class RozetkaImportTests(publication_tests.PublicationImportTests):
    def setUp(self):
        super().setUp()
        self.channel = replace(self.channel, kind=ChannelKind.ROZETKA)

    async def test_platform_capability_disables_import_even_for_known_kind(self):
        definition = CodeChannelRegistry().get("rozetka")
        registry = Mock(
            get=Mock(
                return_value=replace(
                    definition,
                    config={
                        **definition.config,
                        "capabilities": {"read_publications": False},
                    },
                )
            )
        )
        starter = PublicationImportStarter(self.runs, self.jobs, self.uuids, registry)
        with self.assertRaises(PublicationImportUnavailableError):
            await starter.start(
                channel=self.channel, tenant_id=self.tenant, now=self.now
            )
        self.jobs.schedule_once.assert_not_awaited()
        self.assertEqual(self.runs.values, {})

    async def test_stream_overlap_observes_once_and_repeat_keeps_revision(self):
        api = RozetkaFixtureApi()
        normalizer = RozetkaPublicationNormalizer(PublicationHtmlSanitizer())
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(api.handle)
        ) as client:
            source = RozetkaPublicationSource(PublicationJsonClient(client), normalizer)
            snapshots = []
            for _ in range(2):
                run = await self.start()
                checkpoint = "{}"
                for _ in range(20):
                    page = await source.read_page(
                        PublicationSourceConnection(
                            "rozetka",
                            {"username": "fixture-user"},
                            {"password": "secret"},
                        ),
                        checkpoint,
                    )
                    run = await self.import_page(run, page)
                    if page.next_checkpoint is None:
                        break
                    checkpoint = page.next_checkpoint
                self.assertEqual(run.status, "succeeded")
                self.assertEqual(run.resources, 5)
                snapshots.append(
                    {
                        p.external_id: (p.id, p.revision)
                        for p in self.publications.values.values()
                    }
                )
            self.assertEqual(snapshots[0], snapshots[1])

    async def import_page(self, run, page):
        from src.modules.channels.application.publication_import_run.command.import_publication_page.command import (
            ImportPublicationPageCommand,
        )
        from src.modules.channels.application.publication_import_run.command.import_publication_page.handler import (
            ImportPublicationPageHandler,
        )

        await ImportPublicationPageHandler(
            self.state, self.publications, self.uuids
        ).execute(
            ImportPublicationPageCommand(
                **self.args(run), expected_pages=run.pages, page=page
            )
        )
        return self.runs.values[run.id]
