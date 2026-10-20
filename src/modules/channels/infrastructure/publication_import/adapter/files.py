from src.modules.shared.domain.domain_error import DomainError
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.channels.application.publication_import.port.files import (
    PublicationImportImageContentDTO,
)
from typing import BinaryIO
from src.modules.shared.infrastructure.content.images import IMAGE_FILE_SUFFIXES
from uuid import UUID
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.handler import (
    FindUsedImageFilesHandler,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.query import (
    FindUsedImageFilesQuery,
)
from src.modules.files.application.stored_file.command.trash_file.handler import (
    TrashFileHandler,
)
from src.modules.files.application.stored_file.command.trash_file.command import (
    TrashFileCommand,
)
from src.modules.files.application.stored_file.command.lock_ready_file.handler import (
    LockReadyFileHandler,
)
from src.modules.files.application.stored_file.command.lock_ready_file.command import (
    LockReadyFileCommand,
)
from src.modules.files.domain.error import FileNotFoundError


class FilesPublicationImportAdapter:
    """Использует только публичные операции Files и Catalog без чужих SQL-моделей."""

    def __init__(
        self,
        images: CatalogImageFilesPort,
        usage: FindUsedImageFilesHandler,
        lock_ready: LockReadyFileHandler,
        trash: TrashFileHandler,
    ) -> None:
        """Получает фасады на общей сессии внешнего UoW."""
        self.images, self.usage, self.lock_ready, self.trash = (
            images,
            usage,
            lock_ready,
            trash,
        )

    async def upload(
        self, tenant_id: UUID, source: BinaryIO, size_bytes: int, content_type: str
    ) -> UUID:
        """Переиспользует проверки изображений Catalog и upload Files."""
        suffix = IMAGE_FILE_SUFFIXES.get(content_type, "bin")
        result = await self.images.upload(
            tenant_id, source, size_bytes, "publication." + suffix, content_type
        )
        return result.file_id

    async def release(
        self, tenant_id: UUID, actor_id: UUID, file_ids: tuple[UUID, ...]
    ) -> None:
        """Сериализуется с прикреплением Catalog и не трогает уже используемые файлы."""
        for file_id in sorted(set(file_ids)):
            try:
                await self.lock_ready.execute(LockReadyFileCommand(tenant_id, file_id))
            except FileNotFoundError:
                continue
            used = await self.usage.execute(
                FindUsedImageFilesQuery(tenant_id, (file_id,))
            )
            if file_id not in used.file_ids:
                await self.trash.execute(TrashFileCommand(tenant_id, file_id, actor_id))

    async def content(
        self, tenant_id: UUID, file_id: UUID
    ) -> PublicationImportImageContentDTO:
        """Преобразует публичный результат владельца файлов в DTO потребителя."""
        try:
            result = await self.images.content(tenant_id, file_id)
        except DomainError as error:
            raise ChannelsNotFoundError("import_image_not_found") from error
        return PublicationImportImageContentDTO(
            result.content_type, result.size_bytes, result.stream
        )
