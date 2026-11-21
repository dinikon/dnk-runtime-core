import logging

from src.modules.catalog.application.catalog_item.port.stock_events import (
    CatalogStockEventsPort,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

logger = logging.getLogger(__name__)


class CatalogItemMutationService:
    """Координирует загрузку и сохранение под блокировкой товара."""

    def __init__(
        self,
        repository: CatalogItemRepositoryProtocol,
        lock: CatalogMutationLockPort,
        events: CatalogStockEventsPort | None = None,
    ) -> None:
        """Принимает порты, собранные на одной сессии внешнего UoW."""
        self._repository = repository
        self._lock = lock
        self._events = events
        self._tenant_id: EntityIdVO | None = None

    async def load(
        self, tenant_id: EntityIdVO, item_id: CatalogItemIdVO
    ) -> CatalogItem:
        """Загружает актуальный товар под его транзакционной блокировкой."""
        await self._lock.acquire_item(tenant_id, item_id)
        item = await self._repository.get(item_id)
        self._tenant_id = tenant_id

        logger.debug(
            "Catalog item loaded for mutation",
            extra={
                "event": "catalog.mutation.loaded",
                "tenant_id": str(tenant_id.uuid),
                "item_id": str(item.id.uuid),
            },
        )
        return item

    async def save(self, item: CatalogItem) -> None:
        """Сохраняет доменное изменение; commit остаётся у внешнего UoW."""
        await self._repository.save(item)
        events = item.pull_stock_events()
        if self._events is not None and self._tenant_id is not None:
            for event in events:
                await self._events.publish(tenant_id=self._tenant_id.uuid, event=event)
        logger.debug(
            "Catalog mutation prepared for external commit",
            extra={
                "event": "catalog.mutation.prepared",
                "item_id": str(item.id.uuid),
            },
        )
