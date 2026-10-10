from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.catalog.application.category.command.create_category.command import (
    CreateCategoryCommand,
)
from src.modules.catalog.application.category.command.create_category.dto import (
    CreateCategoryResultDTO,
)
from src.modules.catalog.application.category.port.tree import CategoryTreePort


class CreateCategoryHandler:
    """Координирует создание category на портах общего tenant UoW."""

    def __init__(
        self,
        repository: CategoryRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
        locales: LocalePort,
        tree: CategoryTreePort,
    ) -> None:
        """Принимает необходимые порты без привязки к SQL."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._uuid = uuid
        self._locales = locales
        self._tree = tree

    async def execute(self, command: CreateCategoryCommand) -> CreateCategoryResultDTO:
        """Проверяет locale и создаёт агрегат; commit выполняет внешняя сборка."""
        await self._lock.acquire(command.tenant_id)
        locale = LocaleVO(command.locale)
        await self._locales.ensure_active(locale.value)
        entity = Category.create(
            CategoryIdVO(self._uuid.new()),
            command.parent_id,
            await self._tree.ancestors(command.parent_id),
            locale,
            command.label,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.add(entity)
        return CreateCategoryResultDTO(entity.id.uuid, entity.revision)
