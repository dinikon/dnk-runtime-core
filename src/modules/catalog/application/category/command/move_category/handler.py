from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol
from src.modules.catalog.application.category.port.tree import CategoryTreePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.category.command.move_category.command import (
    MoveCategoryCommand,
)
from src.modules.catalog.application.category.command.move_category.dto import (
    MoveCategoryResultDTO,
)


class MoveCategoryHandler:
    """Координирует перемещение и чтение предков под одним transaction lock."""

    def __init__(
        self,
        repository: CategoryRepositoryProtocol,
        tree: CategoryTreePort,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
    ) -> None:
        """Принимает порты внешней сборки одного UoW."""
        self._repository = repository
        self._tree = tree
        self._lock = lock
        self._clock = clock

    async def execute(self, command: MoveCategoryCommand) -> MoveCategoryResultDTO:
        """Передаёт снимок предков домену и сохраняет проверенное состояние."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.category_id)
        entity.ensure_revision(command.expected_revision)
        entity.move(
            command.parent_id,
            await self._tree.ancestors(command.parent_id),
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(entity)
        return MoveCategoryResultDTO(entity.id.uuid, entity.revision)
