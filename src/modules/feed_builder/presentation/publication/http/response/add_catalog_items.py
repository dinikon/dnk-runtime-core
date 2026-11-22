from uuid import UUID
from pydantic import BaseModel


class AddedPublicationResponse(BaseModel):
    """Показывает результат для одной нормализованной выбранной позиции."""

    id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    status: str
    version: int
    outcome: str


class AddCatalogItemsResponse(BaseModel):
    """Возвращает стабильные идентификаторы после атомарного пакета."""

    feed_id: UUID
    feed_version: int
    items: tuple[AddedPublicationResponse, ...]
