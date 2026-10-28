from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.catalog_item.query.get_catalog_variant_image_content.query import (
    GetCatalogVariantImageContentQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_variant_image_content.dto import (
    GetCatalogVariantImageContentResultDTO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_variant.query import (
    GetCatalogVariantQuery,
)
from src.modules.catalog.application.catalog_item.port.query_repository import (
    CatalogItemQueryRepositoryProtocol,
)
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.error import CatalogNotFoundError


class GetCatalogVariantImageContentHandler:
    """Разрешает назначение изображения через read порт и открывает Files stream."""

    def __init__(
        self,
        repository: CatalogItemQueryRepositoryProtocol,
        files: CatalogImageFilesPort,
        clock: ClockPort,
    ) -> None:
        """Принимает порты чтения и закрываемого потока."""
        self._repository = repository
        self._files = files
        self._clock = clock

    async def execute(
        self, query: GetCatalogVariantImageContentQuery
    ) -> GetCatalogVariantImageContentResultDTO:
        """Не допускает произвольный file ID вне галереи item."""
        LocaleVO(query.locale)
        result = await self._repository.get_variant(
            GetCatalogVariantQuery(
                query.tenant_id, query.item_id, query.variant_id, query.locale
            ),
            self._clock.now(),
        )
        gallery = result.item.effective_gallery
        image = (
            next((i for i in gallery.images if i.id == query.image_id), None)
            if gallery
            else None
        )
        if image is None:
            raise CatalogNotFoundError("Изображение отсутствует в галерее.")
        value = await self._files.content(query.tenant_id.uuid, image.file_id)
        return GetCatalogVariantImageContentResultDTO(
            value.file_id,
            value.name,
            value.content_type,
            value.size_bytes,
            value.stream,
        )
