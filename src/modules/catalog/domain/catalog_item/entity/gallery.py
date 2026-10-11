from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import dataclass
from typing import Self
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage


@dataclass(frozen=True, slots=True)
class CatalogItemGallery:
    """Собственный локализованный набор; пустой набор блокирует наследование."""

    images: tuple[CatalogItemImage, ...]
    primary_image_id: EntityIdVO | None

    @classmethod
    def create(
        cls, images: tuple[CatalogItemImage, ...], primary_image_id: EntityIdVO | None
    ) -> Self:
        """Собирает набор для проверки через границу CatalogItem."""
        return cls(images, primary_image_id)

    @classmethod
    def restore(
        cls, images: tuple[CatalogItemImage, ...], primary_image_id: EntityIdVO | None
    ) -> Self:
        """Восстанавливает набор без исправления основного изображения."""
        return cls(images, primary_image_id)
