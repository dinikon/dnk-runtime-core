"""Переходы доставки и контракт WooCommerce без внешних запросов."""

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from src.modules.channels.application.content_delivery.contracts import (
    PreparedContentRequest,
    ContentWriteOutcome,
)
from src.modules.channels.application.content_media.contracts import (
    PreparedGallery,
    PreparedGalleryImage,
)
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.domain.content_delivery.aggregate import ContentDelivery
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.channels.domain.content_delivery.value_object import (
    DeliveryContextVO,
    DeliveryStatus,
)
from src.modules.channels.domain.content_media.value_object import MediaTransferStatus
from src.modules.channels.domain.product_representation.value_object import (
    ContentOrigin,
    ContentOrigins,
    FieldOrigin,
    LocalizedContent,
)
from src.modules.channels.infrastructure.platforms.woocommerce.content import (
    WooContentAdapter,
)
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def context() -> DeliveryContextVO:
    """Создаёт полное подтверждённое намерение существующей цели."""
    return DeliveryContextVO(
        *(EntityIdVO(uuid4()) for _ in range(4)),
        2,
        1,
        1,
        "a" * 64,
        "woocommerce.site",
        "https://shop.example",
        "101",
        None,
        "simple",
        "uk",
        "position",
    )


class ContentDeliveryDomainTests(TestCase):
    """Проверяет доменную атомарность, поколения и неизменяемый снимок попытки."""

    def setUp(self) -> None:
        self.now = datetime.now(UTC)
        self.context = context()
        self.job = EntityIdVO(uuid4())
        self.value = ContentDelivery.create(
            representation_id=EntityIdVO(uuid4()),
            publication_id=EntityIdVO(uuid4()),
            context=self.context,
            job_id=self.job,
            now=self.now,
        )

    def begin(self) -> None:
        self.assertTrue(
            self.value.begin_attempt(
                job_id=self.job,
                encrypted_request=b"encrypted",
                schema="woocommerce.content.v1",
                content_hash="b" * 64,
                media=(),
                now=self.now,
            )
        )

    def test_new_request_preserves_running_snapshot_and_requires_new_generation(
        self,
    ) -> None:
        self.begin()
        next_context = replace(self.context, content_fingerprint="c" * 64)
        self.value.request_update(
            context=next_context, job_id=EntityIdVO(uuid4()), now=self.now
        )
        self.assertEqual(
            (self.value.requested_generation, self.value.sending_generation), (2, 1)
        )
        self.assertEqual(self.value.prepared_context, self.context)
        self.assertTrue(
            self.value.complete_attempt(
                job_id=self.job,
                generation=1,
                content_hash="b" * 64,
                fields=("title",),
                error_code=None,
                uncertain=False,
                now=self.now,
            )
        )
        self.assertEqual(self.value.applied_generation, 1)
        self.assertTrue(self.value.queue_next(job_id=EntityIdVO(uuid4()), now=self.now))
        self.assertEqual(self.value.status, DeliveryStatus.QUEUED)
        self.assertEqual(self.value.applied_generation, 1)

    def test_unknown_blocks_resend_and_reconciliation_preserves_request(self) -> None:
        self.begin()
        self.value.complete_attempt(
            job_id=self.job,
            generation=1,
            content_hash="b" * 64,
            fields=(),
            error_code="network_timeout",
            uncertain=True,
            now=self.now,
        )
        self.assertFalse(
            self.value.begin_attempt(
                job_id=self.job,
                encrypted_request=b"other",
                schema="v1",
                content_hash="d" * 64,
                media=(),
                now=self.now,
            )
        )
        self.value.request_update(
            context=replace(self.context, content_fingerprint="c" * 64),
            job_id=EntityIdVO(uuid4()),
            now=self.now,
        )
        self.assertFalse(
            self.value.queue_next(job_id=EntityIdVO(uuid4()), now=self.now)
        )
        self.value.request_reconciliation(
            expected_revision=self.value.revision,
            job_id=EntityIdVO(uuid4()),
            now=self.now,
        )
        self.assertEqual(self.value.prepared_request_encrypted, b"encrypted")
        self.assertEqual(self.value.sending_generation, 1)

    def test_duplicate_generation_wrong_job_and_bad_revision_leave_state(self) -> None:
        self.assertFalse(
            self.value.request_update(
                context=self.context, job_id=EntityIdVO(uuid4()), now=self.now
            )
        )
        self.assertEqual(self.value.revision, 1)
        self.begin()
        before = asdict(self.value)
        self.assertFalse(
            self.value.complete_attempt(
                job_id=EntityIdVO(uuid4()),
                generation=1,
                content_hash="b" * 64,
                fields=(),
                error_code=None,
                uncertain=False,
                now=self.now,
            )
        )
        with self.assertRaises(ContentDeliveryError):
            self.value.complete_attempt(
                job_id=self.job,
                generation=1,
                content_hash="b" * 64,
                fields=(),
                error_code=None,
                uncertain=True,
                now=self.now,
            )
        with self.assertRaises(ContentDeliveryError):
            self.value.request_update(
                context=self.context,
                job_id=EntityIdVO(uuid4()),
                now=self.now - timedelta(seconds=1),
            )
        self.assertEqual(asdict(self.value), before)

    def test_restore_rejects_contradictions(self) -> None:
        values = {
            field: getattr(self.value, field)
            for field in self.value.__dataclass_fields__
        }
        for invalid in (
            {"revision": 0},
            {"requested_generation": True},
            {"status": DeliveryStatus.IN_FLIGHT},
            {"error_code": "unexpected"},
            {"applied_generation": 1},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ContentDeliveryError):
                ContentDelivery.restore(**(values | invalid))


class WooContentTests(IsolatedAsyncioTestCase):
    """Проверяет разрешённые поля, адреса и запрет слепых повторов."""

    def setUp(self) -> None:
        self.http = Mock()
        self.http.request = AsyncMock()
        self.adapter = WooContentAdapter(self.http)
        self.config = WooCommerceConfig.model_validate(
            {"version": 1, "endpoint": "https://shop.example/wordpress", "settings": {}}
        )
        self.credentials = WooCommerceCredentials(
            consumer_key="key", consumer_secret="secret"
        )
        origin = FieldOrigin(ContentOrigin.CATALOG, EntityIdVO(uuid4()))
        self.content = LocalizedContent(
            "uk", "Name", "<p>Body</p>", None, ContentOrigins(origin, origin, origin)
        )

    def prepared(
        self, *, variant: bool = False, gallery: bool = False, remote: bool = False
    ) -> tuple[PreparedContentRequest, PreparedGalleryImage]:
        value = (
            replace(context(), publication_kind="variant", parent_external_id="10")
            if variant
            else context()
        )
        image = PreparedGalleryImage(
            uuid4(),
            1,
            uuid4(),
            "Front",
            "",
            "70" if remote else None,
            MediaTransferStatus.READY if remote else MediaTransferStatus.PENDING,
            "https://tenant.example/image.png?token=secret",
        )
        pictures = (
            PreparedGallery(
                uuid4(),
                "101",
                "10" if variant else None,
                value.publication_kind,
                "uk",
                (image,),
            )
            if gallery
            else None
        )
        request = self.adapter.prepare(
            context=value,
            content=self.content,
            gallery=pictures,
            reserved_media_ids=(image.media_id,) if gallery and not remote else (),
        )
        return request, image

    def observed(self, *, title: str = "Name", images: list | None = None) -> dict:
        return {
            "id": 101,
            "type": "simple",
            "name": title,
            "description": "<p>Body</p>",
            "images": images or [],
            "sku": "keep",
            "regular_price": "10.00",
            "stock_quantity": 5,
            "attributes": [],
        }

    async def test_product_updates_only_content_and_repeat_uses_confirmed_ids(
        self,
    ) -> None:
        request, image = self.prepared(gallery=True)
        self.http.request.side_effect = [
            self.observed(title="Old"),
            self.observed(images=[{"id": 70, "alt": "Front"}]),
        ]
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=False,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.CONFIRMED)
        self.assertEqual(result.media[0].media_id, image.media_id)
        call = self.http.request.call_args_list[-1]
        self.assertEqual(set(call.kwargs["body"]), {"name", "description", "images"})
        self.assertIn("src", call.kwargs["body"]["images"][0])
        self.assertNotIn("secret", repr(request))
        repeat, _ = self.prepared(gallery=True, remote=True)
        body = self.adapter.decode(repeat).product
        self.assertIsNotNone(body)
        self.assertNotIn(
            "src", body.model_dump(mode="json", exclude_none=True)["images"][0]
        )

    async def test_timeout_and_uncertain_upload_never_repeat_put(self) -> None:
        request, _ = self.prepared(gallery=True)
        self.http.request.side_effect = [
            self.observed(title="Old"),
            VerificationFailure("network_timeout", retryable=True),
        ]
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=False,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.UNKNOWN)
        self.http.request.reset_mock()
        self.http.request.side_effect = [
            self.observed(images=[{"id": 70, "alt": "Front"}])
        ]
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=True,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.UNKNOWN)
        self.assertEqual(
            [call.args[0] for call in self.http.request.call_args_list], ["GET"]
        )

    async def test_reconciliation_of_known_media_and_body_is_confirmed(self) -> None:
        request, _ = self.prepared(gallery=True, remote=True)
        self.http.request.return_value = self.observed(
            images=[{"id": 70, "alt": "Front"}]
        )
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=True,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.CONFIRMED)
        self.assertEqual(set(result.fields), {"title", "body", "gallery"})

    async def test_variant_targets_parent_path_without_name_or_attributes(self) -> None:
        request, _ = self.prepared(variant=True)
        self.http.request.side_effect = [
            {
                "id": 101,
                "parent_id": 10,
                "type": "variation",
                "description": "Old",
                "image": None,
            },
            {
                "id": 101,
                "parent_id": 10,
                "type": "variation",
                "description": "<p>Body</p>",
                "image": None,
            },
        ]
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=False,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.CONFIRMED)
        call = self.http.request.call_args_list[-1]
        self.assertIn("/products/10/variations/101", call.args[1])
        self.assertEqual(call.kwargs["body"], {"description": "<p>Body</p>"})

    async def test_preflight_rejects_changed_kind_and_explicit_empty_is_preserved(
        self,
    ) -> None:
        request, _ = self.prepared()
        self.http.request.return_value = self.observed() | {"type": "variable"}
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=False,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.REJECTED)
        self.assertEqual(self.http.request.await_count, 1)
        empty = self.adapter.prepare(
            context=context(),
            content=replace(self.content, body="", gallery=()),
            gallery=PreparedGallery(uuid4(), "101", None, "simple", "uk", ()),
            reserved_media_ids=(),
        )
        body = self.adapter.decode(empty).product
        self.assertEqual(body.model_dump(mode="json", exclude_none=True)["images"], [])
        self.assertEqual(body.description, "")

    async def test_variation_parent_is_checked_before_put(self) -> None:
        """Неверный parent из ответа не может переместить вариацию в другой контейнер."""
        request, _ = self.prepared(variant=True)
        self.http.request.return_value = {
            "id": 101,
            "parent_id": 999,
            "type": "variation",
            "description": "Old",
            "image": None,
        }
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=False,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.REJECTED)
        self.assertEqual(result.error_code, "content_target_changed")
        self.assertEqual(self.http.request.await_count, 1)

    async def test_wordpress_paragraph_formatting_does_not_hide_content_changes(
        self,
    ) -> None:
        """Plain text и внешний перевод строки wpautop допустимы; потеря текста — нет."""
        request = self.adapter.prepare(
            context=context(),
            content=replace(self.content, body="Plain body"),
            gallery=None,
            reserved_media_ids=(),
        )
        self.http.request.side_effect = [
            self.observed(title="Old"),
            self.observed() | {"description": "<p>Plain body</p>\n"},
        ]
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=False,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.CONFIRMED)
        self.http.request.side_effect = [
            self.observed() | {"description": "<p>Different body</p>\n"}
        ]
        result = await self.adapter.execute(
            config=self.config,
            credentials=self.credentials,
            request=request,
            reconcile=True,
        )
        self.assertEqual(result.outcome, ContentWriteOutcome.UNKNOWN)
