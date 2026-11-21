from typing import Protocol
from uuid import UUID

from src.modules.catalog.domain.catalog_item.stock_event import CatalogStockChanged


class CatalogStockEventsPort(Protocol):
    """Доставка фактов количественных изменений после общей фиксации."""

    async def publish(self, *, tenant_id: UUID, event: CatalogStockChanged) -> None:
        """Записывает интеграционное событие в outbox текущего UoW."""
        ...
