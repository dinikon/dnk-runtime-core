from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.usage import CatalogItemUsagePort
from src.modules.catalog.application.catalog_item.structure_service import (
    CatalogItemStructureService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.catalog_item.command.replace_catalog_item_structure.command import (
    ReplaceCatalogItemStructureCommand,
)
from src.modules.catalog.application.catalog_item.command.replace_catalog_item_structure.dto import (
    ReplaceCatalogItemStructureResultDTO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


class ReplaceCatalogItemStructureHandler:
    """Координирует replace_catalog_item_structure; товарные инварианты остаются в CatalogItem."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        structures: CatalogItemStructureService,
        usage: CatalogItemUsagePort,
    ) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock
        self._structures = structures
        self._usage = usage

    async def execute(
        self, command: ReplaceCatalogItemStructureCommand
    ) -> ReplaceCatalogItemStructureResultDTO:
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        if command.item_id != root.id:
            raise InvalidCatalogValueError(
                "Структура и вид изменяются только по ID корня."
            )
        now = self._clock.now()
        children, definitions = await self._structures.prepare(
            command.structure, root.id, command.actor_id, now, root
        )
        used = await self._usage.used_ids(tuple(command.removed_ids))
        root.replace_structure(
            command.structure.axes,
            children,
            command.structure.default_selection,
            definitions,
            command.removed_ids,
            used,
            command.actor_id,
            now,
        )
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return ReplaceCatalogItemStructureResultDTO(
            item.id.uuid,
            root.id.uuid,
            item.revision,
            root.revision,
            tuple(c.id.uuid for c in root.children),
        )
