from dataclasses import dataclass
import hashlib
from uuid import UUID
from anyio import CancelScope

from src.modules.channels.application.content_media.contracts import (
    MediaFile,
    MediaFileChecksum,
    OpenMediaContent,
)
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.files.application.port.query_repository import (
    StorageQueryRepositoryProtocol,
)
from src.modules.files.application.port.storage import (
    StorageResolverProtocol,
    FileContentStream,
)
from src.modules.files.application.stored_file.command.lock_ready_file.command import (
    LockReadyFileCommand,
)
from src.modules.files.application.stored_file.command.lock_ready_file.handler import (
    LockReadyFileHandler,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.files.domain.error import FileNotFoundError
from src.modules.shared.infrastructure.content.images import (
    IMAGE_MIME_TYPES,
    IMAGE_FILE_SUFFIXES,
    image_content_type,
)


@dataclass(slots=True)
class InspectedImageStream:
    """Возвращает проверенный префикс и затем исходный поток без потери bytes."""

    source: FileContentStream
    prefix: bytes
    remaining: int

    def __aiter__(self) -> "InspectedImageStream":
        """Возвращает управляемый итератор."""
        return self

    async def __anext__(self) -> bytes:
        """Ограничивает фактическую длину метаданными Files."""
        try:
            if self.prefix:
                chunk, self.prefix = self.prefix, b""
            else:
                chunk = await self.source.__anext__()
            self.remaining -= len(chunk)
            if self.remaining < 0:
                raise ContentMediaError("media_file_invalid")
            return chunk
        except StopAsyncIteration:
            if self.remaining != 0:
                raise ContentMediaError("media_file_invalid") from None
            raise

    async def aclose(self) -> None:
        """Закрывает нижележащий поток при любом исходе."""
        await self.source.aclose()


class FilesMediaGateway:
    """Использует публичные Files-порты; SQL и сеть разделены явными методами."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        queries: StorageQueryRepositoryProtocol,
        lock: LockReadyFileHandler,
        storage: StorageResolverProtocol,
    ) -> None:
        """Получает доверенный tenant и зависимости внешней сборки."""
        self._tenant_id, self._queries, self._lock, self._storage = (
            tenant_id,
            queries,
            lock,
            storage,
        )

    async def describe(
        self, file_ids: tuple[UUID, ...], *, for_update: bool = False
    ) -> tuple[MediaFile, ...]:
        """Проверяет ready и MIME без сетевых операций под блокировкой."""
        result: list[MediaFile] = []
        for identifier in sorted(set(file_ids)):
            if for_update:
                try:
                    await self._lock.execute(
                        LockReadyFileCommand(self._tenant_id, identifier)
                    )
                except DomainError:
                    raise ContentMediaError("media_file_unavailable") from None
            location = await self._queries.content_location(self._tenant_id, identifier)
            if (
                location is None
                or location.content_type not in IMAGE_MIME_TYPES
                or not 0 < location.size_bytes <= 10 * 1024 * 1024
            ):
                raise ContentMediaError("media_file_unavailable")
            # Files запрещает перезапись: новый бинарный объект получает новый file UUID.
            fingerprint = hashlib.sha256(f"files.v1:{identifier}".encode()).hexdigest()
            result.append(
                MediaFile(
                    identifier,
                    fingerprint,
                    IMAGE_FILE_SUFFIXES[location.content_type],
                    location,
                )
            )
        return tuple(result)

    async def open(self, file: MediaFile) -> OpenMediaContent:
        """Подтверждает ownership и raster-заголовок вне SQL-транзакции."""
        location = file.location
        storage = self._storage.resolve(location.location)
        try:
            if not await storage.exists_owned(location.location, location.key):
                raise ContentMediaError("media_file_unavailable")
            stream = await storage.open(location.location, location.key)
        except FileNotFoundError:
            raise ContentMediaError("media_file_unavailable") from None
        try:
            prefix = b""
            while len(prefix) < min(4096, location.size_bytes):
                try:
                    prefix += await stream.__anext__()
                except StopAsyncIteration:
                    break
            if (
                len(prefix) > location.size_bytes
                or image_content_type(prefix[:4096]) != location.content_type
            ):
                raise ContentMediaError("media_file_invalid")
            return OpenMediaContent(
                location.content_type,
                location.size_bytes,
                InspectedImageStream(stream, prefix, location.size_bytes),
            )
        except BaseException:
            with CancelScope(shield=True):
                await stream.aclose()
            raise

    async def inspect(self, files: tuple[MediaFile, ...]) -> None:
        """Читает ограниченный префикс каждого изображения без удержания SQL locks."""
        await self.checksums(files)

    async def checksums(
        self, files: tuple[MediaFile, ...]
    ) -> tuple[MediaFileChecksum, ...]:
        """Хеширует проверенный поток целиком и закрывает его при любом исходе."""
        result: list[MediaFileChecksum] = []
        for file in files:
            content = await self.open(file)
            digest = hashlib.sha256()
            try:
                async for chunk in content.stream:
                    digest.update(chunk)
            finally:
                with CancelScope(shield=True):
                    await content.stream.aclose()
            result.append(MediaFileChecksum(file.file_id, digest.hexdigest()))
        return tuple(result)
