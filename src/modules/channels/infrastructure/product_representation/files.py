from uuid import UUID

from src.modules.files.application.port.query_repository import (
    StorageQueryRepositoryProtocol,
)
from src.modules.files.application.stored_file.command.lock_ready_file.handler import (
    LockReadyFileHandler,
)
from src.modules.files.application.stored_file.command.lock_ready_file.command import (
    LockReadyFileCommand,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.infrastructure.content.images import IMAGE_MIME_TYPES


class RepresentationFilesGateway:
    """Использует только публичные Files-контракты на общей tenant-сессии."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        files: StorageQueryRepositoryProtocol,
        lock_ready: LockReadyFileHandler,
    ) -> None:
        """Захватывает доверенный tenant из внешней сборки, без сетевого клиента."""
        self._tenant_id = tenant_id
        self._files = files
        self._lock_ready = lock_ready

    async def unavailable(
        self, file_ids: tuple[UUID, ...], *, for_update: bool = False
    ) -> tuple[UUID, ...]:
        """Проверяет MIME и ready; чужие, удалённые и неготовые файлы не различает."""
        unavailable: list[UUID] = []
        for file_id in sorted(set(file_ids)):
            if for_update:
                try:
                    await self._lock_ready.execute(
                        LockReadyFileCommand(self._tenant_id, file_id)
                    )
                except DomainError:
                    unavailable.append(file_id)
                    continue
            file = await self._files.content_location(self._tenant_id, file_id)
            if file is None or file.content_type not in IMAGE_MIME_TYPES:
                unavailable.append(file_id)
        return tuple(unavailable)
