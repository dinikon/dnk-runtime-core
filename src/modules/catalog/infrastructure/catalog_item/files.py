from src.modules.files.application.stored_file.command.lock_ready_file.handler import (
    LockReadyFileHandler,
)
from src.modules.files.application.stored_file.command.lock_ready_file.command import (
    LockReadyFileCommand,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.catalog.domain.error import CatalogNotFoundError
from typing import BinaryIO
from src.modules.shared.infrastructure.content.images import (
    IMAGE_MIME_TYPES,
    image_content_type,
)
from uuid import UUID
from src.modules.catalog.application.catalog_item.port.files import (
    UploadedCatalogImageFile,
    CatalogImageFileContent,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.files.application.stored_file.command.upload_file.handler import (
    UploadFileHandler,
)
from src.modules.files.application.stored_file.command.upload_file.command import (
    UploadFileCommand,
)
from src.modules.files.application.stored_file.query.get_file_content.handler import (
    GetFileContentHandler,
)
from src.modules.files.application.stored_file.query.get_file_content.query import (
    GetFileContentQuery,
)


class FilesCatalogImages:
    """Адаптер публичных Files-сценариев без чужих ORM и FK."""

    def __init__(
        self,
        upload: UploadFileHandler,
        content: GetFileContentHandler,
        lock_ready: LockReadyFileHandler,
    ) -> None:
        """Получает публичные handlers на общем UoW."""
        self._upload = upload
        self._content = content
        self._lock_ready = lock_ready

    async def upload(
        self,
        tenant_id: UUID,
        source: BinaryIO,
        size_bytes: int,
        name: str,
        content_type: str,
    ) -> UploadedCatalogImageFile:
        """Проверяет ограниченный raster-файл перед записью в Files."""
        if not 0 < size_bytes <= 10 * 1024 * 1024:
            raise InvalidCatalogValueError("Изображение должно быть не более 10 MiB.")
        source.seek(0)
        header = source.read(4096)
        source.seek(0)
        detected_type = image_content_type(header)
        if detected_type is None:
            raise InvalidCatalogValueError(
                "Разрешены PNG, JPEG, WebP, GIF, AVIF и BMP."
            )
        try:
            result = await self._upload.execute(
                UploadFileCommand(tenant_id, source, size_bytes, name, detected_type)
            )
        except DomainError as exc:
            raise InvalidCatalogValueError(
                "Files не допускает загрузку изображения."
            ) from exc
        return UploadedCatalogImageFile(
            result.file_id, result.name, result.content_type, result.size_bytes
        )

    async def ensure_images(self, tenant_id: UUID, file_ids: tuple[UUID, ...]) -> None:
        """Проверяет доступность файлов текущего tenant, закрывая каждый поток."""
        for identifier in sorted(set(file_ids)):
            try:
                await self._lock_ready.execute(
                    LockReadyFileCommand(tenant_id, identifier)
                )
            except DomainError as exc:
                raise CatalogNotFoundError(
                    "Файл изображения недоступен для текущего tenant."
                ) from exc
            result = await self.content(tenant_id, identifier)
            await result.stream.aclose()
            if result.content_type not in IMAGE_MIME_TYPES:
                raise InvalidCatalogValueError(
                    "Файл не является поддерживаемым изображением."
                )

    async def content(self, tenant_id: UUID, file_id: UUID) -> CatalogImageFileContent:
        """Открывает Files stream с проверкой tenant владения."""
        try:
            value = await self._content.execute(GetFileContentQuery(tenant_id, file_id))
        except DomainError as exc:
            raise CatalogNotFoundError(
                "Файл изображения недоступен для текущего tenant."
            ) from exc
        return CatalogImageFileContent(
            value.file_id,
            value.name,
            value.content_type,
            value.size_bytes,
            value.stream,
        )
