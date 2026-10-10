from src.modules.catalog.domain.attribute.repository import AttributeRepositoryProtocol
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.application.attribute.command.delete_attribute.command import (
    DeleteAttributeCommand,
)


class DeleteAttributeHandler:
    """Координирует delete_attribute на портах общего tenant UoW."""

    def __init__(
        self,
        repository: AttributeRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает только необходимые порты текущего сценария."""
        self._repository = repository
        self._lock = lock

    async def execute(self, command: DeleteAttributeCommand) -> None:
        """Выполняет сценарий; доменные решения и commit остаются у владельцев."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.attribute_id)
        entity.ensure_revision(command.expected_revision)
        entity.ensure_deletable(await self._repository.is_used(entity.id))
        await self._repository.delete(entity)
