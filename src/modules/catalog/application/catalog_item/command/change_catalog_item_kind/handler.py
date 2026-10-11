from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.usage import CatalogItemUsagePort
from src.modules.catalog.application.catalog_item.structure_service import (
    CatalogItemStructureService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.catalog_item.command.change_catalog_item_kind.command import (
    ChangeCatalogItemKindCommand,
)
from src.modules.catalog.application.catalog_item.command.change_catalog_item_kind.dto import (
    ChangeCatalogItemKindResultDTO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.domain.error import InvalidCatalogValueError


class ChangeCatalogItemKindHandler:
    """Координирует change_catalog_item_kind; товарные инварианты остаются в CatalogItem."""

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
        self, command: ChangeCatalogItemKindCommand
    ) -> ChangeCatalogItemKindResultDTO:
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        if command.item_id != root.id:
            raise InvalidCatalogValueError(
                "Структура и вид изменяются только по ID корня."
            )
        now = self._clock.now()
        used = bool(
            await self._usage.used_ids(tuple(i.id for i in (root, *root.children)))
        )
        if command.kind == CatalogItemKind.VARIABLE and command.structure is not None:
            children, definitions = await self._structures.prepare(
                command.structure, root.id, command.actor_id, now
            )
            if (
                command.carry_to_index is not None
                and not 0 <= command.carry_to_index < len(children)
            ):
                raise InvalidCatalogValueError(
                    "Номер варианта для переноса отсутствует."
                )
            carry = (
                children[command.carry_to_index].id
                if command.carry_to_index is not None
                else None
            )
            root.change_to_variable(
                command.structure.axes,
                children,
                command.structure.default_selection,
                definitions,
                carry,
                used,
                command.actor_id,
                now,
            )
        elif (
            command.kind == CatalogItemKind.SIMPLE
            and command.selected_item_id is not None
        ):
            root.change_to_simple(
                command.selected_item_id,
                command.discarded_ids,
                used,
                command.actor_id,
                now,
            )
        else:
            raise InvalidCatalogValueError("Нужна полная структура перехода.")
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return ChangeCatalogItemKindResultDTO(
            item.id.uuid,
            root.id.uuid,
            item.revision,
            root.revision,
            tuple(c.id.uuid for c in root.children),
        )
