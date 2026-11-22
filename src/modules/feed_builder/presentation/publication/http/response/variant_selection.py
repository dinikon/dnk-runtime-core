from uuid import UUID
from pydantic import BaseModel


class VariantSelectionItemResponse(BaseModel):
    """Передаёт одну явную пару ID из фиксированного снимка Catalog."""

    catalog_item_id: UUID
    catalog_variant_id: UUID
    title: str | None
    sku: str | None


class VariantSelectionResponse(BaseModel):
    """Возвращает полный набор до ста вариантов без создания публикаций."""

    items: tuple[VariantSelectionItemResponse, ...]
