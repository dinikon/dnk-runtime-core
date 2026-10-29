import asyncio
from uuid import UUID, uuid5
import hashlib
import httpcore
from src.config import dnk_config
from src.modules.catalog.infrastructure.catalog_import.download import (
    download_public_file,
)
from src.modules.catalog.infrastructure.catalog_import.media import ImportMediaRuntime
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.files.application.port.storage import StorageUnavailableError
from src.modules.files.domain.error import FilesError
from src.modules.shared.infrastructure.content.images import (
    image_content_type,
    IMAGE_FILE_SUFFIXES,
)


class PublicationImageDownloader:
    """Переиспользует безопасный downloader и двухфазные Files без таблицы импорта."""

    def __init__(self, runtime: ImportMediaRuntime) -> None:
        """Получает внешнюю сборку коротких Files транзакций."""
        self.runtime = runtime
        self.semaphore = asyncio.Semaphore(
            dnk_config.CATALOG_IMPORT.download_concurrency
        )

    async def download(
        self, identifier: UUID, url: str
    ) -> tuple[UUID | None, str | None]:
        """Сохраняет доступное изображение либо возвращает безопасное предупреждение."""
        async with self.semaphore:
            return await self._download(identifier, url)

    async def _download(
        self, identifier: UUID, url: str
    ) -> tuple[UUID | None, str | None]:
        """Ограничивает сетевую фазу и закрывает временный файл при любом исходе."""
        try:
            file = await download_public_file(
                url,
                dnk_config.CATALOG_IMPORT.image_max_bytes,
                min(60, dnk_config.CATALOG_IMPORT.download_timeout_seconds),
            )
            try:
                mime = image_content_type(file.source.read(4096))
                if mime is None:
                    return None, "Изображение пропущено: неподдерживаемый формат."
                file.source.seek(0)
                digest = hashlib.sha256()
                while chunk := file.source.read(65536):
                    digest.update(chunk)
                file.source.seek(0)
                file_id = uuid5(
                    identifier,
                    "image:"
                    + hashlib.sha256(url.encode()).hexdigest()
                    + ":"
                    + digest.hexdigest(),
                )
                await self.runtime.put(
                    file_id,
                    file.source,
                    file.size,
                    f"publication-{file_id}.{IMAGE_FILE_SUFFIXES[mime]}",
                    mime,
                )
                return file_id, None
            finally:
                file.source.close()
        except (
            InvalidCatalogValueError,
            StorageUnavailableError,
            FilesError,
            OSError,
            TimeoutError,
            httpcore.NetworkError,
            httpcore.TimeoutException,
            httpcore.ProtocolError,
        ):
            return (
                None,
                "Изображение пропущено: не удалось загрузить или сохранить файл.",
            )
