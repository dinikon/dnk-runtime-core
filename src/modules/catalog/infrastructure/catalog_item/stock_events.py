from uuid import UUID, uuid4

from src.modules.catalog.application.catalog_item.stock_events import (
    stock_changed_event,
)
from src.modules.catalog.domain.catalog_item.stock_event import CatalogStockChanged
from src.modules.shared.application.events.outbox_repository_protocol import (
    OutboxRepositoryProtocol,
)


class CatalogStockEvents:
    """Сохраняет интеграционные события Catalog в outbox общей транзакции."""

    def __init__(self, outbox: OutboxRepositoryProtocol) -> None:
        """Принимает outbox текущего UoW."""
        self.outbox = outbox

    async def publish(self, *, tenant_id: UUID, event: CatalogStockChanged) -> None:
        """Сохраняет один envelope для последующей доставки в брокер."""
        integration = stock_changed_event(
            tenant_id=tenant_id, event_id=uuid4(), event=event
        )
        await self.outbox.add(integration)
