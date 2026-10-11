from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.catalog_item.command.set_catalog_item_primary_image.command import (
    SetCatalogItemPrimaryImageCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_primary_image.dto import (
    SetCatalogItemPrimaryImageResultDTO,
)


class SetCatalogItemPrimaryImageHandler:
    """Координирует set_catalog_item_primary_image; товарные инварианты остаются в CatalogItem."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        locales: LocalePort,
    ) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock
        self._locales = locales

    async def execute(
        self, command: SetCatalogItemPrimaryImageCommand
    ) -> SetCatalogItemPrimaryImageResultDTO:
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        now = self._clock.now()
        await self._locales.ensure_active(command.locale)
        root.set_primary_image(
            command.item_id,
            LocaleVO(command.locale),
            EntityIdVO(command.image_id),
            command.actor_id,
            now,
        )
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return SetCatalogItemPrimaryImageResultDTO(
            item.id.uuid, root.id.uuid, item.revision, root.revision
        )
