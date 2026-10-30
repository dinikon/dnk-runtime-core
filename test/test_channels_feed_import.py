"""Контракты Domain и Prom: один POST, отчёт и независимая сверка контента."""

from dataclasses import replace, asdict
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from src.modules.channels.application.content_feed.contracts import (
    FeedSnapshot,
    FeedGroupSnapshot,
    FeedPublicationKey,
    FeedOverlay,
    RenderedFeed,
)
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.domain.content_feed.delivery import (
    FeedDeliveryVO,
    FeedDeliveryPhase as Phase,
    FeedImportContextVO,
    FeedImportReportVO,
)
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.infrastructure.content_feed.delivery_document import (
    encode_delivery,
    decode_delivery,
    DELIVERY_SCHEMA,
)
from src.modules.channels.infrastructure.platforms.prom.feed_import import (
    PromFeedImporter,
    PromImportDocument,
)
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.infrastructure.platforms.prom.feed_serializer import (
    PromYmlSerializer,
)
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.crypto.fernet_cipher import FernetCipher
from cryptography.fernet import Fernet
from test.test_channels_content_feed import feed, target, XML


class FeedImportDomainTests(TestCase):
    def setUp(self) -> None:
        """Создаёт включённый фид и намерение без внешних запросов."""
        self.cipher = FernetCipher(Fernet.generate_key().decode())
        self.value = feed(self.cipher)
        self.now = self.value.updated_at
        self.value.enable(
            expected_revision=1, blockers=(), actor=self.value.updated_by, now=self.now
        )
        self.operation = EntityIdVO(uuid4())
        self.job = EntityIdVO(uuid4())
        self.context = FeedImportContextVO(2, 1, "prom.root_group", "store", "a" * 64)

    def request(self) -> None:
        """Начинает отдельную ревизию прогресса."""
        self.value.request_import(
            operation_id=self.operation,
            actor_id=self.value.updated_by,
            job_id=self.job,
            expected_revision=2,
            expected_delivery_revision=0,
            force_update=False,
            now=self.now,
        )

    def test_progress_keeps_configuration_revision_and_repeat_is_idempotent(
        self,
    ) -> None:
        """Проверки worker не должны прерывать постоянный XML endpoint."""
        self.request()
        self.assertFalse(
            self.value.request_import(
                operation_id=self.operation,
                actor_id=self.value.updated_by,
                job_id=self.job,
                expected_revision=2,
                expected_delivery_revision=0,
                force_update=False,
                now=self.now,
            )
        )
        self.value.begin_submission(
            context=self.context, encrypted_request=b"cipher", now=self.now
        )
        self.value.record_acceptance(
            external_id="77", job_id=EntityIdVO(uuid4()), now=self.now
        )
        self.value.record_report(
            report=FeedImportReportVO("SUCCESS", created=0, with_errors_count=0),
            job_id=EntityIdVO(uuid4()),
            now=self.now,
        )
        self.value.record_verification(
            results=(), now=self.now, code="feed_import_content_unconfirmed"
        )
        self.assertEqual(self.value.revision, 2)
        self.assertEqual(self.value.delivery.phase, Phase.COMPLETED)
        self.assertEqual(self.value.delivery.revision, 5)
        self.assertEqual(
            decode_delivery(DELIVERY_SCHEMA, encode_delivery(self.value.delivery)),
            self.value.delivery,
        )

    def test_unknown_requires_explicit_resolution_and_never_resume_post(self) -> None:
        """Неопределённость нельзя снять автоматическим повтором или истечением времени."""
        self.request()
        self.value.begin_submission(
            context=self.context, encrypted_request=b"cipher", now=self.now
        )
        self.value.record_submission_failure(
            code="unknown", uncertain=True, now=self.now
        )
        before = asdict(self.value)
        with self.assertRaises(ContentFeedError):
            self.value.resume_import(
                job_id=self.job, actor_id=self.value.updated_by, now=self.now
            )
        with self.assertRaises(ContentFeedError):
            self.value.request_import(
                operation_id=EntityIdVO(uuid4()),
                actor_id=self.value.updated_by,
                job_id=self.job,
                expected_revision=2,
                expected_delivery_revision=self.value.delivery.revision,
                force_update=False,
                now=self.now,
            )
        self.assertEqual(asdict(self.value), before)
        self.value.resolve_unknown_import(actor_id=self.value.updated_by, now=self.now)
        self.assertEqual(
            self.value.delivery.manual_resolution, "confirmed_not_submitted"
        )
        self.assertFalse(self.value.delivery.busy)

    def test_source_and_delete_are_blocked_but_emergency_disable_works(self) -> None:
        """Отзыв доступа не объявляет внешний импорт отменённым."""
        self.request()
        with self.assertRaises(ContentFeedError):
            self.value.change_source(
                source=self.value.source,
                encrypted_url=b"new",
                expected_revision=2,
                actor=self.value.updated_by,
                now=self.now,
            )
        with self.assertRaises(ContentFeedError):
            self.value.require_delivery_finished()
        self.value.disable(
            expected_revision=2, actor=self.value.updated_by, now=self.now
        )
        self.assertFalse(self.value.enabled)
        self.assertEqual(self.value.delivery.phase, Phase.QUEUED)

    def test_invalid_restore_and_failed_transition_leave_no_partial_change(
        self,
    ) -> None:
        """Отклоняет неподготовленные и противоречивые комбинации фаз."""
        for values in (
            {"revision": -1},
            {"force_update": True},
            {"phase": Phase.PROCESSING, "revision": 1},
            {"phase": "queued"},
        ):
            with self.subTest(values=values), self.assertRaises(ContentFeedError):
                FeedDeliveryVO(**values)
        self.request()
        before = asdict(self.value)
        with self.assertRaises(ContentFeedError):
            self.value.begin_submission(
                context=self.context, encrypted_request=b"", now=self.now
            )
        self.assertEqual(asdict(self.value), before)
        with self.assertRaises(ContentFeedError):
            FeedImportReportVO("SUCCESS", updated=-1)
        self.assertEqual(decode_delivery(DELIVERY_SCHEMA, {}), FeedDeliveryVO())


class PromFeedImportTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        """Готовит нативный XML и независимые состояния существующих товаров."""
        self.target = replace(target(), external_id="99")
        rendered = PromYmlSerializer().render(
            source=XML,
            settings=FeedSourceVO("prom.yml.v1", {}),
            overlays=(
                FeedOverlay(self.target.publication_id.uuid, "001", self.target, None),
            ),
        )
        snapshot = FeedSnapshot(
            uuid4(),
            1,
            (FeedGroupSnapshot(uuid4(), 1, 1, 1, (self.target,)),),
            (FeedPublicationKey(self.target.publication_id.uuid, 1, "001"),),
        )
        self.document = RenderedFeed(rendered.content, rendered.statistics, snapshot)
        self.remote = {
            "id": 99,
            "external_id": "001",
            "name": "Old",
            "name_multilang": {},
            "description": "Old body",
            "description_multilang": {},
            "images": [],
        }
        self.unmatched = {
            "id": 100,
            "external_id": "002",
            "name": "Unmatched",
            "images": [],
        }
        self.post_result = {"status": "success", "id": "77"}
        self.poll_result = {
            "status": "SUCCESS",
            "total": 2,
            "updated": 1,
            "created": 0,
            "with_errors_count": 0,
        }
        self.http = Mock()
        self.calls = []

        async def request(
            method: str, url: str, *, headers: dict | None = None, body: object = None
        ) -> object:
            """Сохраняет только тестовые вызовы, не делает внешнего I/O."""
            self.calls.append((method, url, headers, body))
            if method == "POST":
                return self.post_result
            if "import/status" in url:
                return self.poll_result
            if "products/list" in url:
                return {"products": [self.remote, self.unmatched]}
            return {"product": self.remote}

        self.http.request = AsyncMock(side_effect=request)
        self.importer = PromFeedImporter(self.http)
        self.config = ConnectionConfigVO.create(
            version=1, endpoint="https://my.prom.ua", settings={}
        )
        self.credentials = b'{"token":"real-secret"}'

    async def prepare(self) -> bytes:
        """Использует реальный preflight и кодирование документа пакета."""
        return await self.importer.prepare(
            config=self.config,
            credentials=self.credentials,
            document=self.document,
            feed_url="https://api.example/api/channels/content-feeds/id/feed.xml?token=feed-secret",
            force_update=False,
        )

    async def test_fixed_fields_real_credentials_and_distinct_acceptance_and_report(
        self,
    ) -> None:
        """Цены и остатки исключены из запроса независимо от исходного XML."""
        payload = await self.prepare()
        self.assertNotIn(
            "feed-secret", repr(PromImportDocument.model_validate_json(payload))
        )
        accepted = await self.importer.submit(
            config=self.config, credentials=self.credentials, payload=payload
        )
        self.assertEqual((accepted.outcome, accepted.external_id), ("accepted", "77"))
        post = next(call for call in self.calls if call[0] == "POST")
        self.assertEqual(post[2]["Authorization"], "Bearer real-secret")
        self.assertEqual(
            set(post[3]["updated_fields"]),
            {"name", "description", "name_ua", "description_ua", "images_urls"},
        )
        self.assertFalse(post[3]["only_update"])
        self.assertFalse(post[3]["only_available"])
        self.assertEqual(post[3]["mark_missing_product_as"], "none")
        self.assertIn("feed-secret", post[3]["url"])
        report = await self.importer.poll(
            config=self.config, credentials=self.credentials, external_id="77"
        )
        self.assertEqual(report.report.status, "SUCCESS")

    async def test_post_timeout_unparseable_success_and_5xx_are_unknown(self) -> None:
        """Ни один неоднозначный исход не приводит к повтору POST внутри адаптера."""
        payload = await self.prepare()
        for result in ({"status": "success"}, {"anything": "else"}):
            self.post_result = result
            outcome = await self.importer.submit(
                config=self.config, credentials=self.credentials, payload=payload
            )
            self.assertEqual(outcome.outcome, "unknown")
        for code in (
            "network_timeout",
            "provider_unavailable",
            "provider_response_invalid",
        ):
            self.http.request.side_effect = VerificationFailure(code)
            before = self.http.request.await_count
            result = await self.importer.submit(
                config=self.config, credentials=self.credentials, payload=payload
            )
            self.assertEqual(result.outcome, "unknown")
            self.assertEqual(self.http.request.await_count, before + 1)
        self.http.request.side_effect = VerificationFailure("invalid_credentials")
        self.assertEqual(
            (
                await self.importer.submit(
                    config=self.config, credentials=self.credentials, payload=payload
                )
            ).outcome,
            "rejected",
        )

    async def test_unknown_poll_and_report_errors_do_not_leak_provider_text(
        self,
    ) -> None:
        """Документированный финальный статус и безопасные счётчики обязательны."""
        for report in (
            {"status": "RUNNING"},
            {"status": "SUCCESS", "updated": "1"},
            {},
        ):
            self.poll_result = report
            self.assertIsNone(
                (
                    await self.importer.poll(
                        config=self.config,
                        credentials=self.credentials,
                        external_id="77",
                    )
                ).report
            )
        self.poll_result = {
            "status": "PARTIAL",
            "errors": [
                {"download_images": {"message": "https://example?token=secret"}}
            ],
        }
        result = await self.importer.poll(
            config=self.config, credentials=self.credentials, external_id="77"
        )
        self.assertEqual(result.report.status, "PARTIAL")
        self.assertNotIn("token", repr(result))
        self.assertEqual(result.report.issues[0].stage, "download_images")

    async def test_unmatched_stale_content_and_new_products_block_post(self) -> None:
        """Полный фид не должен незаметно менять несопоставленный контент или создавать товары."""
        self.unmatched["name"] = "Changed in Prom"
        with self.assertRaises(FeedBuildError) as issue:
            await self.prepare()
        self.assertEqual(issue.exception.code, "feed_import_unmatched_content_changed")
        self.unmatched["name"] = "Unmatched"
        self.unmatched["external_id"] = "different"
        with self.assertRaises(FeedBuildError) as issue:
            await self.prepare()
        self.assertEqual(issue.exception.code, "feed_import_would_create_product")
        self.assertFalse(any(call[0] == "POST" for call in self.calls))

    async def test_verification_independent_fields_and_gallery_evidence(self) -> None:
        """Одинаковое число CDN-фотографий не считается совпадением файлов."""
        payload = await self.prepare()
        self.remote.update(
            name=self.target.content[0].title,
            description=self.target.content[0].body,
            name_multilang={"uk": self.target.content[1].title},
            description_multilang={"uk": self.target.content[1].body},
        )
        results = await self.importer.verify(
            config=self.config, credentials=self.credentials, payload=payload
        )
        self.assertTrue(all(f.status == "confirmed" for f in results[0].fields))
        document = PromImportDocument.model_validate_json(payload)
        changed = document.model_copy(
            update={
                "expected": (
                    document.expected[0].model_copy(
                        update={
                            "pictures": (
                                "https://files.example/image.png?token=private",
                            )
                        }
                    ),
                )
            }
        )
        self.remote["images"] = [
            {"url": "https://images.prom.ua/123_w200_h200_photo.jpg"}
        ]
        results = await self.importer.verify(
            config=self.config,
            credentials=self.credentials,
            payload=changed.model_dump_json().encode(),
        )
        self.assertEqual(results[0].fields[-1].status, "unconfirmed")
        self.assertEqual(
            results[0].observed_gallery, ("https://images.prom.ua/123_photo.jpg",)
        )
