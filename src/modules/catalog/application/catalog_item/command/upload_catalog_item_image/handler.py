from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.application.catalog_item.command.upload_catalog_item_image.command import (
    UploadCatalogItemImageCommand,
)
from src.modules.catalog.application.catalog_item.command.upload_catalog_item_image.dto import (
    UploadCatalogItemImageResultDTO,
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


class UploadCatalogItemImageHandler:
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
        self, command: UploadCatalogItemImageCommand
    ) -> UploadCatalogItemImageResultDTO:
        """Проверяет галерею до внешней загрузки и сохраняет новое назначение."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        await self._locales.ensure_active(command.locale)
        identifier = self._uuid.new()
        now = self._clock.now()
        # Domain проверяет кандидат до записи внешнего файла.
        root.ensure_can_add_image(
            command.item_id,
            LocaleVO(command.locale),
            CatalogItemImage.create(
                EntityIdVO(identifier),
                EntityIdVO(identifier),
                0,
                command.alt,
                command.caption,
            ),
            command.main,
            command.actor_id,
            now,
        )
        uploaded = await self._files.upload(
            command.tenant_id.uuid,
            command.source,
            command.size_bytes,
            command.name,
            command.content_type,
        )
        root.add_image(
            command.item_id,
            LocaleVO(command.locale),
            CatalogItemImage.create(
                EntityIdVO(identifier),
                EntityIdVO(uploaded.file_id),
                0,
                command.alt,
                command.caption,
            ),
            command.main,
            command.actor_id,
            now,
        )
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return UploadCatalogItemImageResultDTO(
            item.id.uuid,
            root.id.uuid,
            identifier,
            uploaded.file_id,
            item.revision,
            root.revision,
        )
