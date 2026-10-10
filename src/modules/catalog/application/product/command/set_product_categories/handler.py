from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.product.port.classification_references import (
    ClassificationReferencesPort,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.product.command.set_product_categories.command import (
    SetProductCategoriesCommand,
)
from src.modules.catalog.application.product.command.set_product_categories.dto import (
    SetProductCategoriesResultDTO,
)


class SetProductCategoriesHandler:
    """Координирует замещение categories на портах одного tenant UoW."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        references: ClassificationReferencesPort,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
    ) -> None:
        """Принимает только порты, требуемые этим сценарием."""
        self._repository = repository
        self._references = references
        self._lock = lock
        self._clock = clock

    async def execute(
        self, command: SetProductCategoriesCommand
    ) -> SetProductCategoriesResultDTO:
        """Проверяет ссылки, вызывает доменный метод и сохраняет весь Product."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.product_id)
        entity.ensure_revision(command.expected_revision)
        entity.set_categories(
            command.category_ids,
            command.primary_category_id,
            await self._references.categories(command.category_ids),
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(entity)
        return SetProductCategoriesResultDTO(entity.id.uuid, entity.revision)
