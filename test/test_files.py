"""Предметные инварианты и контракт потокового адаптера."""

from src.modules.shared.domain.value_object.entity_id import EntityIdVO

import asyncio
from datetime import UTC, datetime
from io import BytesIO
import threading
import time
import unittest
from uuid import uuid4
from unittest.mock import Mock
from src.config.infrastructure.files_config import FilesSettings
from src.modules.files.domain.storage_provider.aggregate import StorageProvider
from src.modules.files.domain.bucket.aggregate import Bucket
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.value_object.bucket_name import BucketNameVO
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.files.domain.error import (
    InvalidFileError,
    InvalidStorageStateError,
    SystemProviderImmutableError,
)
from src.modules.files.infrastructure.storage.minio_adapter import (
    MinioStorageAdapter,
    MinioFileContentStream,
    SizedFileReader,
)
from src.modules.files.infrastructure.storage.resolver import StorageResolver
from src.modules.files.application.port.storage import (
    StorageConfigurationError,
    StorageLocation,
)


class FileDomainTests(unittest.TestCase):
    """Проверяет правила в Domain, а не в mapper или HTTP."""

    def test_system_provider_is_immutable_and_restore_checks_invariants(self) -> None:
        """Системное подключение нельзя изменить; неправильная конфигурация не восстанавливается."""
        provider = StorageProvider.create(
            provider_id=EntityIdVO.from_value(uuid4()),
            name="MinIO",
            kind="minio",
            is_system=True,
            config_ref="system_minio",
        )
        with self.assertRaises(SystemProviderImmutableError):
            provider.rename("Changed")
        with self.assertRaises(InvalidStorageStateError):
            StorageProvider.restore(
                provider_id=provider.id,
                name="MinIO",
                kind="drive",
                is_system=True,
                config_ref="system_minio",
            )

    def test_file_and_bucket_transitions(self) -> None:
        """Готовность достигается только через доменные переходы."""
        bucket = Bucket.create(
            bucket_id=EntityIdVO.from_value(uuid4()),
            provider_id=EntityIdVO.from_value(uuid4()),
            name=BucketNameVO(f"dnk-tenant-{uuid4().hex}"),
        )
        with self.assertRaises(InvalidStorageStateError):
            bucket.ensure_ready()
        bucket.mark_ready()
        bucket.ensure_ready()
        bucket.mark_purged()
        with self.assertRaises(InvalidStorageStateError):
            bucket.mark_ready()
        file = StoredFile.create(
            file_id=EntityIdVO.from_value(uuid4()),
            bucket_id=bucket.id,
            name=FileNameVO("image.png"),
            content_type="image/png",
            size=FileSizeVO(2),
            created_at=datetime.now(UTC),
        )
        with self.assertRaises(InvalidFileError):
            file.mark_uploaded(1)
        file.mark_uploaded(2)
        self.assertEqual(file.status, "ready")
        with self.assertRaises(InvalidFileError):
            file.mark_uploaded(2)

    def test_invalid_names_sizes_and_source_lengths(self) -> None:
        """Проверяет пустые файлы и несовпадающую длину источника."""
        for value in (-1, True, "2"):
            with self.assertRaises(InvalidFileError):
                FileSizeVO(value)
        for name in ("", "../x", "a\nfile", "x\\y"):
            with self.assertRaises(InvalidFileError):
                FileNameVO(name)
        for source, size in [(b"a", 2), (b"abc", 2)]:
            reader = SizedFileReader(BytesIO(source), size, time.monotonic() + 60)
            with self.assertRaises(InvalidFileError):
                while reader.read(1):
                    pass
                reader.finish()
        reader = SizedFileReader(BytesIO(), 0, time.monotonic() + 60)
        reader.finish()

    def test_registry_supports_other_adapters_without_minio_types(self) -> None:
        """Расширение реестра не требует изменений handler."""
        fake = Mock()
        resolver = StorageResolver({("drive", "test"): lambda: fake})
        location = StorageLocation(uuid4(), uuid4(), "folder", "drive", "test")
        self.assertIs(resolver.resolve(location), fake)
        with self.assertRaises(StorageConfigurationError):
            StorageResolver({}).resolve(location)


class FileStreamTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет освобождение ресурсов и завершение внешних эффектов при отмене."""

    async def test_stream_closes_on_eof_and_read_failure(self) -> None:
        """Окончание и ошибка чтения освобождают response и соединение."""
        adapter = MinioStorageAdapter(
            FilesSettings(
                endpoint="localhost:9000",
                access_key="test",
                secret_key="test",
                secure=False,
            )
        )
        for fail in (False, True):
            response = Mock()
            response.read.side_effect = OSError() if fail else [b"abc", b""]
            stream = MinioFileContentStream(response, adapter)
            if fail:
                with self.assertRaises(Exception):
                    await anext(stream)
            else:
                self.assertEqual(b"".join([part async for part in stream]), b"abc")
            await stream.aclose()
            response.close.assert_called_once()
            response.release_conn.assert_called_once()

    async def test_cancel_waits_for_thread_before_releasing_resource(self) -> None:
        """Отмена не оставляет внешнюю операцию выполняться после release admission."""
        adapter = MinioStorageAdapter(
            FilesSettings(
                endpoint="localhost:9000",
                access_key="test",
                secret_key="test",
                secure=False,
            )
        )
        started, release = threading.Event(), threading.Event()

        def work() -> None:
            started.set()
            release.wait(5)

        task = asyncio.create_task(adapter.call(work))
        await asyncio.to_thread(started.wait, 2)
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_cancel_open_closes_response_created_in_background(self) -> None:
        """Response не теряется при отмене во время get_object."""
        adapter = MinioStorageAdapter(
            FilesSettings(
                endpoint="localhost:9000",
                access_key="test",
                secret_key="test",
                secure=False,
            )
        )
        response = Mock()
        started, release = threading.Event(), threading.Event()

        def open_response(bucket_name: str, key: str) -> object:
            started.set()
            release.wait(5)
            return response

        adapter._client.get_object = Mock(side_effect=open_response)
        tenant = uuid4()
        location = StorageLocation(
            tenant, uuid4(), f"dnk-tenant-{tenant.hex}", "minio", "system_minio"
        )
        task = asyncio.create_task(adapter.open(location, uuid4().hex))
        await asyncio.to_thread(started.wait, 2)
        task.cancel()
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        response.close.assert_called_once()
        response.release_conn.assert_called_once()
