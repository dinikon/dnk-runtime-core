from dataclasses import dataclass
from datetime import datetime
from src.modules.catalog.application.catalog_item.read_dto import CatalogItemReadDTO
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
)


@dataclass(frozen=True, slots=True)
class GetCatalogItemsPublicationSnapshotResultDTO:
    """Конкретный результат сценария get_catalog_items_publication_snapshot."""

    items: tuple[CatalogItemReadDTO, ...]
    schema: ProductTypeSchemaSnapshot
    locale: str
    as_of: datetime
