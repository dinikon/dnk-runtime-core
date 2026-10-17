import logging
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
    """Координирует порядок блокировок, без бизнес-правил."""

    def __init__(
        self,
        repository: CatalogItemRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает порты, собранные на одной сессии внешнего UoW."""
        self._repository = repository
        self._lock = lock

    async def load(
        self, tenant_id: EntityIdVO, item_id: CatalogItemIdVO, expected_revision: int
    ) -> CatalogItem:
        """Блокирует справочные ссылки и товар, затем проверяет доменную ревизию."""
        await self._lock.acquire_reference(tenant_id)
        await self._lock.acquire_item(tenant_id, item_id)
        item = await self._repository.get(item_id)
        item.ensure_revision(expected_revision)
        logger.debug(
            "Catalog item loaded for mutation",
            extra={
                "event": "catalog.mutation.loaded",
                "tenant_id": str(tenant_id.uuid),
                "item_id": str(item.id.uuid),
                "revision": item.revision,
            },
        )
        return item

    async def save(self, item: CatalogItem) -> None:
        """Сохраняет доменное изменение; commit остаётся у внешнего UoW."""
        await self._repository.save(item)
        logger.debug(
            "Catalog mutation prepared for external commit",
            extra={
                "event": "catalog.mutation.prepared",
                "item_id": str(item.id.uuid),
                "revision": item.revision,
            },
        )
