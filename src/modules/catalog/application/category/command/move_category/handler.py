from src.modules.catalog.application.category.command.move_category.command import (
    MoveCategoryCommand,
)
from src.modules.catalog.application.category.command.move_category.dto import (
    MoveCategoryResultDTO,
)
from src.modules.catalog.domain.category.error import (
    CategoryCycleError,
    CategoryNotFoundError,
)
from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class MoveCategoryHandler:
    def __init__(
        self, repository: CategoryRepositoryProtocol, clock: ClockPort
    ) -> None:
        self._repository, self._clock = repository, clock

    async def execute(self, command: MoveCategoryCommand) -> MoveCategoryResultDTO:
        await self._repository.lock_tree(command.tenant_id)
        category = await self._repository.get_for_update(command.category_id)
        if category is None:
            raise CategoryNotFoundError("Category not found.")
        if command.parent_id is not None:
            if not await self._repository.exists(command.parent_id):
                raise CategoryNotFoundError("Parent category not found.")
            if await self._repository.is_descendant(command.parent_id, category.id):
                raise CategoryCycleError("Category move would create a cycle.")
        category.move_to(
            command.parent_id, actor_id=command.actor_id, now=self._clock.now()
        )
        await self._repository.save_parent(category)
        return MoveCategoryResultDTO(
            category.id.uuid,
            category.parent_id.uuid if category.parent_id else None,
            category.updated_at,
            category.updated_by.uuid,
        )
