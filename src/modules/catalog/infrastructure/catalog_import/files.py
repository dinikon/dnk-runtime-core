from typing import BinaryIO
from uuid import UUID
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
    UploadedCatalogImageFile,
    CatalogImageFileContent,
)
from src.modules.catalog.domain.error import (
    CatalogNotFoundError,
    InvalidCatalogValueError,
)
from src.modules.files.application.artifact.facade import ArtifactFilesFacadeProtocol
from src.modules.files.application.stored_file.command.lock_ready_file.handler import (
    LockReadyFileHandler,
)
from src.modules.files.application.stored_file.command.lock_ready_file.command import (
    LockReadyFileCommand,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.infrastructure.content.images import IMAGE_MIME_TYPES


class FilesCatalogImportImages:
    """Прикрепляет уже проверенные импортом изображения без сети внутри SQL UoW."""

    def __init__(
        self,
        delegate: CatalogImageFilesPort,
        ready: LockReadyFileHandler,
        artifacts: ArtifactFilesFacadeProtocol,
    ) -> None:
        """Получает публичные Files-контракты на общей сессии потребителя."""
        self.delegate, self.ready, self.artifacts = delegate, ready, artifacts

    async def upload(
        self,
        tenant_id: UUID,
        source: BinaryIO,
        size_bytes: int,
        name: str,
        content_type: str,
    ) -> UploadedCatalogImageFile:
        """Сохраняет контракт обычной загрузки для общей сборки сервисов."""
        return await self.delegate.upload(
            tenant_id, source, size_bytes, name, content_type
        )

    async def content(self, tenant_id: UUID, file_id: UUID) -> CatalogImageFileContent:
        """Открывает поток только при явном запросе потребителя."""
        return await self.delegate.content(tenant_id, file_id)

    async def ensure_images(self, tenant_id: UUID, file_ids: tuple[UUID, ...]) -> None:
        """Блокирует готовые Files-ссылки; байты и MIME проверены до этой транзакции."""
        for file_id in sorted(set(file_ids)):
            try:
                await self.ready.execute(LockReadyFileCommand(tenant_id, file_id))
                metadata = await self.artifacts.location(tenant_id, file_id)
            except DomainError as error:
                raise CatalogNotFoundError(
                    "Файл импорта недоступен для текущего tenant."
                ) from error
            if metadata.content_type not in IMAGE_MIME_TYPES:
                raise InvalidCatalogValueError("Файл импорта не является изображением.")
