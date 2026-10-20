"""Граница Catalog/Files: raster validation, tenant IDs и закрытие потоков."""

from io import BytesIO
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from uuid import uuid4
from src.modules.catalog.infrastructure.catalog_item.files import FilesCatalogImages
from src.modules.catalog.domain.error import (
    InvalidCatalogValueError,
    CatalogNotFoundError,
)
from src.modules.files.application.stored_file.command.upload_file.handler import (
    UploadFileHandler,
)
from src.modules.files.application.stored_file.command.upload_file.dto import (
    UploadFileResultDTO,
)
from src.modules.files.application.stored_file.query.get_file_content.handler import (
    GetFileContentHandler,
)
from src.modules.files.application.stored_file.query.get_file_content.dto import (
    GetFileContentResultDTO,
)
from src.modules.files.domain.error import FileNotFoundError


class CatalogFilesAdapterTests(IsolatedAsyncioTestCase):
    """Проверяет потребительский адаптер через публичные контракты владельца."""

    async def asyncSetUp(self) -> None:
        self.upload = AsyncMock(spec=UploadFileHandler)
        self.content = AsyncMock(spec=GetFileContentHandler)
        self.lock_ready = AsyncMock()
        self.adapter = FilesCatalogImages(self.upload, self.content, self.lock_ready)
        self.tenant, self.file_id = uuid4(), uuid4()

    async def test_supported_signatures_and_source_rewind(self) -> None:
        for mime, data in [
            ("image/png", b"\x89PNG\r\n\x1a\nrest"),
            ("image/jpeg", b"\xff\xd8\xffrest"),
            ("image/webp", b"RIFF1234WEBPrest"),
            ("image/gif", b"GIF89a" + b"\x00" * 20),
            ("image/avif", b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00avifmiaf"),
            ("image/bmp", b"BM" + b"\x00" * 12 + b"\x28\x00\x00\x00"),
        ]:
            with self.subTest(mime=mime):
                self.upload.execute.return_value = UploadFileResultDTO(
                    self.file_id, "image", mime, len(data)
                )
                stream = BytesIO(data)
                stream.seek(3)
                result = await self.adapter.upload(
                    self.tenant, stream, len(data), "image", mime
                )
                command = self.upload.execute.call_args.args[0]
                self.assertEqual(command.tenant_id, self.tenant)
                self.assertEqual(command.source.read(), data)
                self.assertEqual(result.file_id, self.file_id)

    async def test_invalid_size_mime_and_signature_never_reach_files(self) -> None:
        for size, mime, data in [
            (0, "image/png", b""),
            (10 * 1024 * 1024 + 1, "image/png", b""),
            (12, "image/png", b"<svg></svg>"),
            (12, "image/svg+xml", b"<svg></svg>"),
            (24, "image/avif", b"\x00\x00\x00\x10ftypisom\x00\x00\x00\x00avif"),
        ]:
            with self.assertRaises(InvalidCatalogValueError):
                await self.adapter.upload(
                    self.tenant, BytesIO(data), size, "image", mime
                )
        self.upload.execute.assert_not_awaited()

    async def test_wrong_declared_mime_does_not_change_image_bytes(self) -> None:
        """WebP под именем jpg сохраняется без конвертации с фактическим MIME."""
        data = b"RIFF1234WEBPrest"
        self.upload.execute.return_value = UploadFileResultDTO(
            self.file_id, "source.jpg", "image/webp", len(data)
        )
        result = await self.adapter.upload(
            self.tenant, BytesIO(data), len(data), "source.jpg", "image/jpeg"
        )
        command = self.upload.execute.call_args.args[0]
        self.assertEqual(command.source.read(), data)
        self.assertEqual(command.content_type, "image/webp")
        self.assertEqual(result.content_type, "image/webp")

    async def test_attachment_validation_closes_stream_and_deduplicates_ids(
        self,
    ) -> None:
        stream = AsyncMock()
        self.content.execute.return_value = GetFileContentResultDTO(
            self.file_id, "image", "image/png", 12, stream
        )
        await self.adapter.ensure_images(self.tenant, (self.file_id, self.file_id))
        self.content.execute.assert_awaited_once()
        stream.aclose.assert_awaited_once()
        query = self.content.execute.call_args.args[0]
        self.assertEqual((query.tenant_id, query.file_id), (self.tenant, self.file_id))
        self.content.execute.return_value = GetFileContentResultDTO(
            self.file_id, "image", "application/pdf", 12, stream
        )
        with self.assertRaises(InvalidCatalogValueError):
            await self.adapter.ensure_images(self.tenant, (self.file_id,))
        self.assertEqual(stream.aclose.await_count, 2)

    async def test_foreign_or_missing_file_becomes_catalog_not_found(self) -> None:
        self.content.execute.side_effect = FileNotFoundError("Provider detail")
        with self.assertRaises(CatalogNotFoundError) as caught:
            await self.adapter.content(self.tenant, self.file_id)
        self.assertIsInstance(caught.exception.__cause__, FileNotFoundError)
        self.assertNotIn("Provider detail", str(caught.exception))

    async def test_attachment_uses_files_lock_and_maps_unavailable_file(self) -> None:
        """Catalog не прикрепляет файл одновременно с очисткой временного импорта."""
        self.lock_ready.execute.side_effect = FileNotFoundError("Already released")
        with self.assertRaises(CatalogNotFoundError):
            await self.adapter.ensure_images(self.tenant, (self.file_id,))
        self.content.execute.assert_not_awaited()
        command = self.lock_ready.execute.call_args.args[0]
        self.assertEqual(
            (command.tenant_id, command.file_id), (self.tenant, self.file_id)
        )
