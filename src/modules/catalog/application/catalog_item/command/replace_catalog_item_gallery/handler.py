from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.catalog_item.command.replace_catalog_item_gallery.command import (
    ReplaceCatalogItemGalleryCommand,
)
from src.modules.catalog.application.catalog_item.command.replace_catalog_item_gallery.dto import (
    ReplaceCatalogItemGalleryResultDTO,
)


class ReplaceCatalogItemGalleryHandler:
    """Координирует replace_catalog_item_gallery; товарные инварианты остаются в CatalogItem."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        locales: LocalePort,
        files: CatalogImageFilesPort,
    ) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock
        self._locales = locales
        self._files = files

    async def execute(
        self, command: ReplaceCatalogItemGalleryCommand
    ) -> ReplaceCatalogItemGalleryResultDTO:
        """Загружает товар, вызывает доменный метод и сохраняет изменение без commit."""
        item = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_revision
        )
        now = self._clock.now()
        await self._locales.ensure_active(command.locale)
        await self._files.ensure_images(
            command.tenant_id.uuid,
            tuple(i.file_id.uuid for i in command.gallery.images),
        )
        item.replace_gallery(
            LocaleVO(command.locale),
            command.gallery,
            command.actor_id,
            now,
        )
        await self._mutations.save(item)
        return ReplaceCatalogItemGalleryResultDTO(item.id.uuid, item.revision)
