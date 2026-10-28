from src.modules.catalog.application.catalog_item.port.publication_usage import (
    CatalogPublicationUsagePort,
)
from src.modules.catalog.application.catalog_item.command.delete_catalog_variant.command import (
    DeleteCatalogVariantCommand,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class DeleteCatalogVariantHandler:
    """Удаляет только entity, принадлежащую заблокированному родителю."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        usage: CatalogPublicationUsagePort,
    ) -> None:
        """Принимает координатор записи и часы."""
        self._mutations, self._clock, self._usage = mutations, clock, usage

    async def execute(self, command: DeleteCatalogVariantCommand) -> None:
        """Проверяет последний вариант Active и сохраняет агрегат без commit."""
        root = await self._mutations.load(command.tenant_id, command.item_id)
        root.remove_variant(
            in_use=await self._usage.used(root.id.uuid, command.variant_id.uuid),
            identifier=command.variant_id,
            actor=command.actor_id,
            now=self._clock.now(),
        )
        await self._mutations.save(root)
