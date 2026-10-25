import asyncio
from uuid import UUID, uuid5
from src.modules.catalog.application.catalog_import.contracts import (
    ImportMediaPort,
    SourceRecord,
)
from src.modules.catalog.application.catalog_import.values import (
    mapped_values,
    image_urls,
    image_texts,
    scalar,
)
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ImportGalleryService:
    """Готовит локализованные галереи через порт загрузки до SQL-фазы товара."""

    def __init__(self, media: ImportMediaPort, max_images: int) -> None:
        """Принимает внешний порт и ограничение размера набора."""
        self.media, self.max_images = media, max_images

    async def prepare(
        self, identifier: UUID, configuration: ImportConfiguration, row: SourceRecord
    ) -> tuple[dict[str, CatalogItemGallery], tuple[str, ...]]:
        """Строит общие или локализованные галереи без SQL-транзакции на время сети."""
        values = mapped_values(configuration, row.values)
        content_locales = {
            key.split("@", 1)[1]
            for key in values
            if key.startswith(("title@", "body@"))
        }
        galleries: dict[str, CatalogItemGallery] = {}
        warnings: list[str] = []
        for mapping in configuration.mappings:
            if mapping.target != "images":
                continue
            base_locale = mapping.locale or configuration.default_locale
            key = "images@" + base_locale
            if key not in values:
                continue
            urls = image_urls(values[key])
            if len(urls) > self.max_images:
                raise InvalidCatalogValueError(
                    "Превышен лимит изображений товара.", ("images",)
                )
            results = await asyncio.gather(
                *(self.media.download(identifier, url) for url in urls)
            )
            locales = (
                {mapping.locale} if mapping.locale else content_locales or {base_locale}
            )
            for locale in locales:
                images: list[CatalogItemImage] = []
                used: set[UUID] = set()
                for i, (file_id, warning) in enumerate(results):
                    if warning:
                        warnings.append(f"Фото: изображение {i + 1}: {warning}")
                    if file_id is None or file_id in used:
                        continue
                    used.add(file_id)
                    alt = values.get(
                        "image_alt@" + locale,
                        values.get("image_alt@" + base_locale, [""]),
                    )
                    caption = values.get(
                        "image_caption@" + locale,
                        values.get("image_caption@" + base_locale, [""]),
                    )
                    alt, caption = image_texts(alt), image_texts(caption)
                    images.append(
                        CatalogItemImage.create(
                            EntityIdVO(
                                uuid5(
                                    identifier,
                                    f"image:{row.number}:{locale}:{file_id}",
                                )
                            ),
                            EntityIdVO(file_id),
                            len(images),
                            alt[min(i, len(alt) - 1)] if alt else "",
                            caption[min(i, len(caption) - 1)] if caption else "",
                        )
                    )
                primary = scalar(values, "primary_image@" + locale) or scalar(
                    values, "primary_image@" + base_locale
                )
                index = 0
                if primary and images:
                    if primary.isdigit() and 1 <= int(primary) <= len(urls):
                        primary_file = results[int(primary) - 1][0]
                        found = next(
                            (
                                i
                                for i, image in enumerate(images)
                                if image.file_id.uuid == primary_file
                            ),
                            None,
                        )
                        if found is None:
                            warnings.append(
                                "Фото: главное изображение недоступно; используется первое загруженное."
                            )
                        else:
                            index = found
                    else:
                        raise InvalidCatalogValueError(
                            "Главное изображение требует порядковый номер от 1."
                        )
                galleries[locale] = CatalogItemGallery.create(
                    tuple(images), images[index].id if images else None
                )
        return galleries, tuple(dict.fromkeys(warnings))
