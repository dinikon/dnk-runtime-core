"""Инварианты доступа, резервация передачи, Files и конкретный Woo-контракт."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from cryptography.fernet import Fernet

from src.modules.channels.domain.content_media.aggregate import ContentMedia
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.domain.content_media.value_object import MediaTransferStatus
from src.modules.channels.application.content_media.contracts import (
    MediaFile,
    PreparedGallery,
    PreparedGalleryImage,
)
from src.modules.channels.infrastructure.content_media.access_tokens import (
    EncryptedMediaTokens,
)
from src.modules.channels.infrastructure.content_media.files import FilesMediaGateway
from src.modules.channels.infrastructure.platforms.woocommerce.media import (
    WooGalleryAdapter,
)
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
)
from src.modules.files.application.port.query_repository import FileContentLocationDTO
from src.modules.files.application.port.storage import StorageLocation
from src.modules.shared.infrastructure.crypto.fernet_cipher import FernetCipher
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.content_media_support import MemoryImageStorage, PNG


class ContentMediaDomainTests(TestCase):
    """Проверяет переходы без SQL и платформы."""

    def setUp(self) -> None:
        """Создаёт реальный зашифрованный токен и первую pending ревизию."""
        self.now = datetime.now(UTC)
        self.tokens = EncryptedMediaTokens(
            cipher=FernetCipher(Fernet.generate_key().decode()),
            base_url="https://tenant.example",
        )
        hashed, encrypted = self.tokens.issue()
        self.media = ContentMedia.create(
            identifier=EntityIdVO(uuid4()),
            connection_id=EntityIdVO(uuid4()),
            file_id=EntityIdVO(uuid4()),
            source_fingerprint="a" * 64,
            metadata_fingerprint="b" * 64,
            token_hash=hashed,
            token_encrypted=encrypted,
            requires_transfer=True,
            now=self.now,
        )

    def test_transfer_reuse_unknown_fencing_and_revocation_are_independent(
        self,
    ) -> None:
        """Unknown не допускает слепой повтор; отзыв не удаляет подтверждённый attachment."""
        operation = EntityIdVO(uuid4())
        self.assertTrue(
            self.media.begin_transfer(
                expected_revision=1, operation_id=operation, now=self.now
            )
        )
        self.assertFalse(
            self.media.record_result(
                expected_revision=self.media.revision,
                operation_id=EntityIdVO(uuid4()),
                remote_id="42",
                error=None,
                uncertain=False,
                now=self.now,
            )
        )
        self.media.record_result(
            expected_revision=self.media.revision,
            operation_id=operation,
            remote_id=None,
            error="network_timeout",
            uncertain=True,
            now=self.now,
        )
        before = replace(self.media)
        with self.assertRaises(ContentMediaError):
            self.media.begin_transfer(
                expected_revision=self.media.revision,
                operation_id=EntityIdVO(uuid4()),
                now=self.now,
            )
        self.assertEqual(self.media, before)
        self.media.record_result(
            expected_revision=self.media.revision,
            operation_id=operation,
            remote_id="42",
            error=None,
            uncertain=False,
            now=self.now,
        )
        self.assertFalse(
            self.media.begin_transfer(
                expected_revision=self.media.revision,
                operation_id=operation,
                now=self.now,
            )
        )
        self.media.revoke(expected_revision=self.media.revision, now=self.now)
        self.assertEqual(self.media.remote_media_id, "42")
        revision = self.media.revision
        self.media.revoke(expected_revision=revision, now=self.now)
        self.assertEqual(self.media.revision, revision)

    def test_invalid_candidates_leave_state_and_audit_unchanged(self) -> None:
        """Фабрики и переходы отклоняют противоречия до присваивания полей."""
        before = replace(self.media)
        with self.assertRaises(ContentMediaError):
            self.media.revoke(expected_revision=True, now=self.now)
        with self.assertRaises(ContentMediaError):
            self.media.revoke(expected_revision=1, now=self.now - timedelta(seconds=1))
        with self.assertRaises(ContentMediaError):
            self.media.renew_access(
                expected_revision=1,
                token_hash=b"bad",
                token_encrypted=b"test",
                now=self.now,
            )
        self.assertEqual(self.media, before)
        self.assertNotIn(self.media.access_token_encrypted.decode(), repr(self.media))

    def test_token_rotation_invalidates_old_url_and_only_accepts_exact_secret(
        self,
    ) -> None:
        """Открытый токен воспроизводится только через Cipher и не входит в Domain repr."""
        old = self.tokens.url(
            self.media.id.uuid, self.media.access_token_encrypted, "image/png"
        ).split("token=")[1]
        self.assertTrue(self.tokens.matches(old, self.media.access_token_hash))
        self.assertFalse(self.tokens.matches(old + "x", self.media.access_token_hash))
        hashed, encrypted = self.tokens.issue()
        self.media.renew_access(
            expected_revision=1,
            token_hash=hashed,
            token_encrypted=encrypted,
            now=self.now,
        )
        self.assertFalse(self.tokens.matches(old, self.media.access_token_hash))


class MediaFilesAndWooTests(IsolatedAsyncioTestCase):
    """Проверяет фактические bytes и первый src / повтор id вне SQL."""

    async def test_storage_signature_length_and_stream_cleanup(self) -> None:
        """Сохраняет префикс, отклоняет поддельный MIME и закрывает источники."""
        tenant, identifier = uuid4(), uuid4()
        storage = MemoryImageStorage()
        storage.objects[(tenant, identifier.hex)] = PNG
        gateway = FilesMediaGateway(
            tenant_id=tenant, queries=Mock(), lock=Mock(), storage=storage
        )
        file = MediaFile(
            identifier,
            "a" * 64,
            "png",
            FileContentLocationDTO(
                StorageLocation(tenant, uuid4(), "test", "minio", "test"),
                identifier.hex,
                "x.png",
                "image/png",
                len(PNG),
            ),
        )
        value = await gateway.open(file)
        self.assertEqual(b"".join([part async for part in value.stream]), PNG)
        await value.stream.aclose()
        self.assertTrue(storage.streams[-1].closed)
        storage.objects[(tenant, identifier.hex)] = b"<html>private</html>"
        with self.assertRaises(ContentMediaError):
            await gateway.inspect((file,))
        self.assertTrue(storage.streams[-1].closed)

    async def test_woo_first_update_uses_src_and_repeat_only_reuses_id(self) -> None:
        """Повтор не передаёт src; альт и порядок сохраняются, варианты не обрезаются."""
        media = uuid4()
        image = PreparedGalleryImage(
            media,
            1,
            uuid4(),
            "Front",
            "",
            None,
            MediaTransferStatus.PENDING,
            "https://tenant.example/image?token=secret",
        )
        gallery = PreparedGallery(uuid4(), "101", None, "simple", "uk", (image,))
        http = Mock()
        http.request = AsyncMock(return_value={"images": [{"id": 77, "alt": "Front"}]})
        adapter = WooGalleryAdapter(http)
        config = WooCommerceConfig.model_validate(
            {"version": 1, "endpoint": "https://shop.example", "settings": {}}
        )
        credentials = WooCommerceCredentials(
            consumer_key="key", consumer_secret="secret"
        )
        with self.assertRaises(ContentMediaError):
            await adapter.update(
                config=config,
                credentials=credentials,
                gallery=gallery,
                reserved_media_ids=(),
            )
        result = await adapter.update(
            config=config,
            credentials=credentials,
            gallery=gallery,
            reserved_media_ids=(media,),
        )
        self.assertEqual(result[0].remote_id, "77")
        self.assertIn("src", http.request.call_args.kwargs["body"]["images"][0])
        repeat = replace(
            gallery,
            images=(
                replace(
                    image,
                    remote_media_id="77",
                    transfer_status=MediaTransferStatus.READY,
                ),
            ),
        )
        await adapter.update(
            config=config,
            credentials=credentials,
            gallery=repeat,
            reserved_media_ids=(),
        )
        self.assertEqual(
            http.request.call_args.kwargs["body"],
            {"images": [{"id": 77, "alt": "Front"}]},
        )
        with self.assertRaises(ContentMediaError):
            adapter.payload(
                replace(
                    repeat,
                    publication_kind="variant",
                    images=(repeat.images[0], repeat.images[0]),
                ),
                (),
            )
