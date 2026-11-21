from uuid import UUID

from src.modules.catalog.domain.catalog_item.stock_event import CatalogStockChanged
from src.modules.shared.domain.events.integration_event import IntegrationEvent

CATALOG_STOCK_CHANGED = "catalog.stock_changed"


def stock_changed_event(
    *, tenant_id: UUID, event_id: UUID, event: CatalogStockChanged
) -> IntegrationEvent:
    """Публичный versioned контракт Catalog без количества, которое может устареть."""
    return IntegrationEvent(
        event_id,
        tenant_id,
        CATALOG_STOCK_CHANGED,
        1,
        "catalog_item",
        event.item_id.uuid,
        {"position_ids": [str(identifier.uuid) for identifier in event.position_ids]},
        event.occurred_at,
    )
