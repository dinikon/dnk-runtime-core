from __future__ import annotations

import logging
import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
import re
import time
from typing import BinaryIO, TypeVar, cast

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import Tags
from urllib3 import HTTPResponse, PoolManager, Retry, Timeout
from urllib3.exceptions import HTTPError

from src.config.infrastructure.files_config import FilesSettings
from src.modules.files.application.port.storage import (
    FileContentStream,
    StorageConfigurationError,
    StorageLocation,
    StorageObject,
    StorageOwnershipError,
    StorageUnavailableError,
)
from src.modules.files.domain.error import FileNotFoundError, InvalidFileError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SizedFileReader:
    """Ограничивает размер и длительность чтения источника без накопления файла."""

    def __init__(self, source: BinaryIO, expected: int, deadline: float) -> None:
        """Сохраняет источник, размер и общий срок передачи."""
        self.source, self.expected, self.deadline = source, expected, deadline
        self.consumed = 0

    def read(self, size: int = -1) -> bytes:
        """Читает ограниченную порцию и запрещает превышение заявленного размера."""
        if time.monotonic() >= self.deadline:
            raise StorageUnavailableError("File transfer deadline exceeded.")
        chunk = self.source.read(size)
        if not chunk and self.consumed < self.expected:
            raise InvalidFileError("File length is shorter than metadata.")
        self.consumed += len(chunk)
        if self.consumed > self.expected:
            raise InvalidFileError("File length exceeds metadata.")
        return chunk

    def finish(self) -> None:
        """Проверяет конец источника, в том числе при пустой загрузке."""
        if self.consumed != self.expected or self.source.read(1):
            raise InvalidFileError("File length does not match metadata.")


class MinioFileContentStream:
    """Читает SDK-response порциями и освобождает HTTP-соединение."""

    def __init__(self, response: HTTPResponse, adapter: MinioStorageAdapter) -> None:
        """Принимает открытый response, который не зависит от DB-сессии."""
        self._response, self._adapter = response, adapter
        self._closed = False
        self._deadline = time.monotonic() + adapter.operation_timeout

    def __aiter__(self) -> AsyncIterator[bytes]:
        """Возвращает поток как асинхронный итератор."""
        return self

    async def __anext__(self) -> bytes:
        """Читает порцию вне event loop; закрывает поток при завершении или сбое."""
        if self._closed:
            raise StopAsyncIteration
        try:
            if time.monotonic() >= self._deadline:
                raise StorageUnavailableError("File read deadline exceeded.")
            chunk = await self._adapter.call(lambda: self._response.read(64 * 1024))
            if chunk:
                return chunk
            await self.aclose()
            raise StopAsyncIteration
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        """Идемпотентно закрывает response и возвращает соединение в pool."""
        if not self._closed:
            self._closed = True
            await self._adapter.call(self._close)

    def _close(self) -> None:
        """Освобождает синхронный HTTP-ресурс SDK."""
        self._response.close()
        self._response.release_conn()


class MinioStorageAdapter:
    """Адаптер закрытого MinIO; не генерирует presigned URL."""

    def __init__(self, settings: FilesSettings) -> None:
        """Создаёт process-local SDK client с ограниченными таймаутами и concurrency."""
        if (
            not settings.endpoint
            or "://" in settings.endpoint
            or "/" in settings.endpoint
            or not settings.access_key.get_secret_value()
            or not settings.secret_key.get_secret_value()
        ):
            raise StorageConfigurationError("Instance MinIO is not configured.")
        self.operation_timeout = settings.operation_timeout_seconds
        self._limit = asyncio.Semaphore(settings.concurrency)
        self._client = Minio(
            settings.endpoint,
            access_key=settings.access_key.get_secret_value(),
            secret_key=settings.secret_key.get_secret_value(),
            secure=settings.secure,
            region=settings.region or None,
            http_client=PoolManager(
                timeout=Timeout(
                    connect=settings.timeout_seconds, read=settings.timeout_seconds
                ),
                retries=Retry(total=0),
                maxsize=settings.concurrency,
            ),
        )

    async def call(self, action: Callable[[], T]) -> T:
        """Не освобождает admission до завершения синхронной операции при отмене."""
        async with self._limit:
            started = time.monotonic()
            task = asyncio.create_task(asyncio.to_thread(action))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                # Поток нельзя остановить отменой coroutine: сначала ждём его завершения.
                await asyncio.gather(task, return_exceptions=True)
                raise
            except S3Error as exc:
                logger.warning(
                    "Storage operation failed",
                    extra={
                        "event": "files.storage.call_failed",
                        "reason_code": exc.code,
                    },
                )
                if exc.code in {"NoSuchKey", "NoSuchObject"}:
                    raise FileNotFoundError("File object was not found.") from None
                if exc.code in {
                    "AccessDenied",
                    "InvalidAccessKeyId",
                    "SignatureDoesNotMatch",
                }:
                    raise StorageConfigurationError(
                        "MinIO credentials do not grant the required access."
                    ) from None
                raise StorageUnavailableError("MinIO operation failed.") from None
            except (HTTPError, OSError, TimeoutError):
                logger.warning(
                    "Storage unavailable",
                    extra={
                        "event": "files.storage.call_failed",
                        "reason_code": "transport_unavailable",
                    },
                )
                raise StorageUnavailableError("MinIO is unavailable.") from None
            finally:
                logger.debug(
                    "Storage operation finished",
                    extra={
                        "event": "files.storage.call_finished",
                        "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    },
                )

    @staticmethod
    def _validate_location(location: StorageLocation) -> None:
        """Запрещает обращение к контейнеру другого tenant через подменённый ID."""
        if location.bucket_name != f"dnk-tenant-{location.tenant_id.hex}":
            raise StorageOwnershipError("Bucket does not belong to tenant.")

    def _owned_bucket(
        self, location: StorageLocation, *, allow_empty_claim: bool = False
    ) -> bool:
        """Подтверждает ownership либо безопасно принимает незавершённое создание."""
        self._validate_location(location)
        if not self._client.bucket_exists(location.bucket_name):
            return False
        tags = self._client.get_bucket_tags(location.bucket_name) or {}
        expected = {
            "dnk_tenant": str(location.tenant_id),
            "dnk_bucket": str(location.bucket_id),
        }
        if dict(tags) != expected:
            # Namespace эксклюзивен модулю; durable регистрация предшествует созданию.
            if (
                not allow_empty_claim
                or tags
                or next(
                    self._client.list_objects(
                        location.bucket_name, recursive=True, include_version=True
                    ),
                    None,
                )
                is not None
            ):
                raise StorageOwnershipError("Bucket ownership is not confirmed.")
            if self._client._list_multipart_uploads(
                location.bucket_name, max_uploads=1
            ).uploads:
                raise StorageOwnershipError(
                    "Incomplete uploads prevent claiming untagged bucket."
                )
            self._client.set_bucket_tags(location.bucket_name, self._tags(expected))
        return True

    @staticmethod
    def _tags(values: dict[str, str]) -> Tags:
        """Преобразует ownership-метки в тип инфраструктурного SDK."""
        tags = Tags.new_bucket_tags()
        tags.update(values)
        return tags

    async def ensure_private_bucket(self, location: StorageLocation) -> None:
        """Восстанавливает подготовку контейнера и проверяет отсутствие публичной policy."""

        def ensure() -> None:
            """Выполняет синхронные шаги подготовки одного контейнера."""
            self._validate_location(location)
            if not self._client.bucket_exists(location.bucket_name):
                try:
                    self._client.make_bucket(location.bucket_name)
                except S3Error as exc:
                    if exc.code not in {
                        "BucketAlreadyOwnedByYou",
                        "BucketAlreadyExists",
                    }:
                        raise
            self._owned_bucket(location, allow_empty_claim=True)
            try:
                policy = self._client.get_bucket_policy(location.bucket_name)
            except S3Error as exc:
                if exc.code != "NoSuchBucketPolicy":
                    raise
            else:
                if policy:
                    raise StorageOwnershipError(
                        "Bucket must not have an access policy."
                    )

        await self.call(ensure)

    async def put(
        self,
        location: StorageLocation,
        key: str,
        source: BinaryIO,
        size_bytes: int,
        content_type: str,
    ) -> int:
        """Записывает поток под новым непрозрачным ключом и проверяет его длину."""

        def upload() -> int:
            """Выполняет ограниченную синхронную передачу объекта."""
            self._validate_location(location)
            reader = SizedFileReader(
                source, size_bytes, time.monotonic() + self.operation_timeout
            )
            self._client.put_object(
                location.bucket_name,
                key,
                cast(BinaryIO, reader),
                size_bytes,
                content_type=content_type,
                metadata={
                    "dnk-tenant": str(location.tenant_id),
                    "dnk-bucket": str(location.bucket_id),
                    "dnk-file": key,
                },
                num_parallel_uploads=1,
            )
            reader.finish()
            return reader.consumed

        return await self.call(upload)

    async def open(self, location: StorageLocation, key: str) -> FileContentStream:
        """Открывает объект для backend-потребителя без URL и redirect."""
        self._validate_location(location)
        response: HTTPResponse | None = None

        def open_response() -> HTTPResponse:
            """Сохраняет response для освобождения даже при отменённом await."""
            nonlocal response
            response = self._client.get_object(location.bucket_name, key)
            return response

        try:
            return MinioFileContentStream(await self.call(open_response), self)
        except asyncio.CancelledError:
            if response is not None:
                await MinioFileContentStream(response, self).aclose()
            raise

    def objects(self, location: StorageLocation) -> AsyncIterator[StorageObject]:
        """Перечисляет объекты лениво, не загружая весь контейнер в память."""
        return self._objects(location)

    async def _objects(self, location: StorageLocation) -> AsyncIterator[StorageObject]:
        """Читает страницы вне event loop с подтверждением ownership контейнера."""
        if not await self.call(lambda: self._owned_bucket(location)):
            return
        objects = self._client.list_objects(
            location.bucket_name, recursive=True, include_user_meta=True
        )
        while True:
            obj = await self.call(lambda: next(objects, None))
            if obj is None:
                return
            meta = {k.lower(): v for k, v in (obj.metadata or {}).items()}
            owned = bool(
                re.fullmatch("[0-9a-f]{32}", obj.object_name or "")
                and meta.get("x-amz-meta-dnk-tenant") == str(location.tenant_id)
                and meta.get("x-amz-meta-dnk-bucket") == str(location.bucket_id)
                and meta.get("x-amz-meta-dnk-file") == obj.object_name
            )
            yield StorageObject(
                obj.object_name or "",
                obj.last_modified or datetime.now(UTC),
                obj.size or 0,
                owned,
            )

    async def remove(self, location: StorageLocation, key: str) -> None:
        """Удаляет известный объект только из подтверждённого контейнера."""
        self._validate_location(location)
        await self.call(lambda: self._client.remove_object(location.bucket_name, key))

    async def abort_incomplete(
        self, location: StorageLocation, older_than: datetime
    ) -> int:
        """Очищает старые multipart uploads без неподдерживаемых lifecycle rules."""

        def cleanup() -> int:
            """Перечисляет передачи страницами под подтверждённым ownership."""
            if not self._owned_bucket(location):
                return 0
            removed = 0
            key_marker: str | None = None
            upload_marker: str | None = None
            while True:
                page = self._client._list_multipart_uploads(
                    location.bucket_name,
                    max_uploads=1000,
                    key_marker=key_marker,
                    upload_id_marker=upload_marker,
                )
                for upload in page.uploads:
                    if (
                        re.fullmatch("[0-9a-f]{32}", upload.object_name)
                        and upload.initiated_time is not None
                        and upload.initiated_time < older_than
                    ):
                        self._client._abort_multipart_upload(
                            location.bucket_name, upload.object_name, upload.upload_id
                        )
                        removed += 1
                if not page.is_truncated or not page.uploads:
                    return removed
                # SDK 7.2.20 не заполняет next_upload_id_marker: используем последнюю пару.
                last = page.uploads[-1]
                key_marker, upload_marker = last.object_name, last.upload_id

        return await self.call(cleanup)

    async def purge(self, location: StorageLocation) -> None:
        """Идемпотентно удаляет owned-контейнер, версии и multipart uploads."""

        def purge_bucket() -> None:
            """Очищает контейнер под внешним exclusive tenant admission."""
            if not self._owned_bucket(location, allow_empty_claim=True):
                return
            for obj in self._client.list_objects(
                location.bucket_name, recursive=True, include_version=True
            ):
                self._client.remove_object(
                    location.bucket_name, obj.object_name, version_id=obj.version_id
                )
            # SDK 7.2.20 не имеет публичного multipart-cleanup; совместимость проверяется тестом.
            while True:
                uploads = self._client._list_multipart_uploads(
                    location.bucket_name, max_uploads=1000
                )
                if not uploads.uploads:
                    break
                for upload in uploads.uploads:
                    self._client._abort_multipart_upload(
                        location.bucket_name, upload.object_name, upload.upload_id
                    )
            self._client.remove_bucket(location.bucket_name)

        await self.call(purge_bucket)
