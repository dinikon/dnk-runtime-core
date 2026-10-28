from dataclasses import replace
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.application.catalog_item.command.upload_catalog_variant_image.command import (
    UploadCatalogVariantImageCommand,
)
from src.modules.catalog.application.catalog_item.command.upload_catalog_variant_image.dto import (
    UploadCatalogVariantImageResultDTO,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class UploadCatalogVariantImageHandler:
    """Связывает Files upload и назначение изображения в одном внешнем UoW."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        files: CatalogImageFilesPort,
        locales: LocalePort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает только порты сценария."""
        self._mutations = mutations
        self._files = files
        self._locales = locales
        self._clock = clock
        self._uuid = uuid

    async def execute(
        self, command: UploadCatalogVariantImageCommand
    ) -> UploadCatalogVariantImageResultDTO:
        """Проверяет галерею до внешней загрузки и сохраняет новое назначение."""
        item = await self._mutations.load(command.tenant_id, command.item_id)
        await self._locales.ensure_active(command.locale)
        identifier = self._uuid.new()
        now = self._clock.now()
        variant = item.variant(command.variant_id)
        gallery = variant.galleries.get(command.locale)
        images = gallery.images if gallery else ()
        image = CatalogItemImage.create(
            EntityIdVO(identifier),
            EntityIdVO(identifier),
            max((i.position for i in images), default=-1) + 1,
            command.alt,
            command.caption,
        )
        primary = image.id if command.main or not images else gallery.primary_image_id
        candidate = variant.changed(
            fields=frozenset({"gallery"}),
            locale=LocaleVO(command.locale),
            gallery=CatalogItemGallery.create((*images, image), primary),
            actor=command.actor_id,
            now=now,
        )
        # Проверка всей семьи выполняется до внешнего Files upload.
        checked = replace(item)
        checked.change_variant(variant=candidate, actor=command.actor_id, now=now)
        uploaded = await self._files.upload(
            command.tenant_id.uuid,
            command.source,
            command.size_bytes,
            command.name,
            command.content_type,
        )
        image = CatalogItemImage.create(
            EntityIdVO(identifier),
            EntityIdVO(uploaded.file_id),
            image.position,
            command.alt,
            command.caption,
        )
        candidate = variant.changed(
            fields=frozenset({"gallery"}),
            locale=LocaleVO(command.locale),
            gallery=CatalogItemGallery.create((*images, image), primary),
            actor=command.actor_id,
            now=now,
        )
        item.change_variant(variant=candidate, actor=command.actor_id, now=now)
        await self._mutations.save(item)
        return UploadCatalogVariantImageResultDTO(
            variant.id.uuid, identifier, uploaded.file_id
        )
