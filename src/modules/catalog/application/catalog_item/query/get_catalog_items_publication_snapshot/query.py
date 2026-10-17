from dataclasses import dataclass
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GetCatalogItemsPublicationSnapshotQuery:
    """Явный вход read сценария get_catalog_items_publication_snapshot."""

    tenant_id: EntityIdVO
    item_ids: tuple[CatalogItemIdVO, ...]
    locale: str
    as_of: datetime | None = None
    expected_revisions: dict[UUID, int] | None = None
