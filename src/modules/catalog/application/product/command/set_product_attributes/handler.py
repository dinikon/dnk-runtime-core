from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.product.port.attribute_definitions import (
    AttributeDefinitionsPort,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.product.command.set_product_attributes.command import (
    SetProductAttributesCommand,
)
from src.modules.catalog.application.product.command.set_product_attributes.dto import (
    SetProductAttributesResultDTO,
)


class SetProductAttributesHandler:
    """Координирует замещение attributes на портах одного tenant UoW."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        references: AttributeDefinitionsPort,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
    ) -> None:
        """Принимает только порты, требуемые этим сценарием."""
        self._repository = repository
        self._references = references
        self._lock = lock
        self._clock = clock

    async def execute(
        self, command: SetProductAttributesCommand
    ) -> SetProductAttributesResultDTO:
        """Проверяет ссылки, вызывает доменный метод и сохраняет весь Product."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.product_id)
        entity.ensure_revision(command.expected_revision)
        entity.set_attributes(
            command.values,
            await self._references.get_definitions(
                tuple(v.attribute_id for v in command.values)
            ),
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(entity)
        return SetProductAttributesResultDTO(entity.id.uuid, entity.revision)
