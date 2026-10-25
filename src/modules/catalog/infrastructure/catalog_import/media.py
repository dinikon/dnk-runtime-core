from contextlib import AbstractAsyncContextManager
from typing import Protocol, BinaryIO
from uuid import UUID, uuid5
import asyncio
import hashlib
import httpcore
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from src.config import dnk_config
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.content.images import (
    image_content_type,
    IMAGE_FILE_SUFFIXES,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_import_media import (
    CatalogImportMediaModel as Media,
)
from src.modules.catalog.infrastructure.catalog_import.download import (
    download_public_file,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


class ImportMediaRuntime(Protocol):
    """Внутренний Infrastructure-контракт коротких SQL-фаз и файлового SDK."""

    def transaction(self) -> AbstractAsyncContextManager[UnitOfWork]:
        """Открывает tenant-транзакцию внешней сборки."""
        ...

    async def put(
        self,
        identifier: UUID,
        source: BinaryIO,
        size: int,
        name: str,
        content_type: str,
    ) -> None:
        """Загружает двухфазный Files-объект вне SQL."""
        ...


class PreparedImportMedia:
    """Infrastructure-адаптер повторяемой загрузки изображений."""

    def __init__(
        self, runtime: ImportMediaRuntime, semaphore: asyncio.Semaphore
    ) -> None:
        """Получает независимые SQL-фазы и общий лимит worker."""
        self.runtime, self.semaphore = runtime, semaphore

    async def download(
        self, identifier: UUID, url: str
    ) -> tuple[UUID | None, str | None]:
        """Повторяет только незавершённую загрузку URL в пределах снимка."""
        digest = hashlib.sha256(url.encode()).hexdigest()
        media_id = uuid5(identifier, "media:" + digest)
        async with self.semaphore:
            async with self.runtime.transaction() as uow:
                row = (
                    (
                        await uow.session.execute(
                            select(Media.__table__).where(Media.id == media_id)
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row:
                    return row["file_id"], row["error"]
            file_id: UUID | None = None
            warning: str | None = None
            try:
                downloaded = await download_public_file(
                    url,
                    dnk_config.CATALOG_IMPORT.image_max_bytes,
                    min(60, dnk_config.CATALOG_IMPORT.download_timeout_seconds),
                )
                try:
                    mime = image_content_type(downloaded.source.read(4096))
                    downloaded.source.seek(0)
                    if mime is None:
                        raise InvalidCatalogValueError(
                            "Недопустимый формат изображения."
                        )
                    content_digest = hashlib.sha256()
                    while chunk := downloaded.source.read(65536):
                        content_digest.update(chunk)
                    downloaded.source.seek(0)
                    file_id = uuid5(media_id, "file:" + content_digest.hexdigest())
                    await self.runtime.put(
                        file_id,
                        downloaded.source,
                        downloaded.size,
                        f"import-{media_id}.{IMAGE_FILE_SUFFIXES[mime]}",
                        mime,
                    )
                finally:
                    downloaded.source.close()
            except (InvalidCatalogValueError, TimeoutError, OSError) as error:
                file_id = None
                warning = (
                    str(error)
                    if isinstance(error, InvalidCatalogValueError)
                    else "Источник изображения недоступен."
                )
            except (
                httpcore.NetworkError,
                httpcore.TimeoutException,
                httpcore.ProtocolError,
            ):
                file_id, warning = None, "Источник изображения недоступен."
            async with self.runtime.transaction() as uow:
                await uow.session.execute(
                    insert(Media)
                    .values(
                        id=media_id,
                        import_id=identifier,
                        url_hash=digest,
                        file_id=file_id,
                        error=warning,
                    )
                    .on_conflict_do_nothing(index_elements=[Media.id])
                )
            return file_id, warning
