from src.modules.catalog.domain.content_block.repository import (
    ContentBlockRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.content_block.command.delete_content_block.command import (
    DeleteContentBlockCommand,
)


class DeleteContentBlockHandler:
    """Координирует delete_content_block; инварианты и переходы принадлежат Domain."""

    def __init__(
        self, repository: ContentBlockRepositoryProtocol, lock: CatalogMutationLockPort
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, command: DeleteContentBlockCommand) -> None:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.content_block_id)
        entity.ensure_revision(command.expected_revision)
        entity.ensure_deletable(await self._repository.is_used(entity.id))
        await self._repository.delete(entity)
