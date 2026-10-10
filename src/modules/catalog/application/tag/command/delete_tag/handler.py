from src.modules.catalog.domain.tag.repository import TagRepositoryProtocol
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.application.tag.command.delete_tag.command import (
    DeleteTagCommand,
)


class DeleteTagHandler:
    """Координирует delete_tag на портах общего tenant UoW."""

    def __init__(
        self,
        repository: TagRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает только необходимые порты текущего сценария."""
        self._repository = repository
        self._lock = lock

    async def execute(self, command: DeleteTagCommand) -> None:
        """Выполняет сценарий; доменные решения и commit остаются у владельцев."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.tag_id)
        entity.ensure_revision(command.expected_revision)
        entity.ensure_deletable(await self._repository.is_used(entity.id))
        await self._repository.delete(entity)
