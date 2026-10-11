import logging
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.application.catalog_item.port.owner_lookup import (
    CatalogItemOwnerLookupPort,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

logger = logging.getLogger(__name__)


class CatalogItemMutationService:
    """Координирует разрешение владельца и порядок блокировок, без бизнес-правил."""

    def __init__(
        self,
        repository: CatalogItemRepositoryProtocol,
        owners: CatalogItemOwnerLookupPort,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает порты, собранные на одной сессии внешнего UoW."""
        self._repository = repository
        self._owners = owners
        self._lock = lock

    async def load(
        self, tenant_id: EntityIdVO, item_id: CatalogItemIdVO, expected_revision: int
    ) -> CatalogItem:
        """Блокирует справочные ссылки и семью, затем проверяет доменную ревизию."""
        await self._lock.acquire_reference(tenant_id)
        root_id = await self._owners.root_id(item_id)
        await self._lock.acquire_family(tenant_id, root_id)
        root = await self._repository.get(root_id)
        root.ensure_revision(expected_revision)
        logger.debug(
            "Catalog family loaded for mutation",
            extra={
                "event": "catalog.mutation.loaded",
                "tenant_id": str(tenant_id.uuid),
                "item_id": str(item_id.uuid),
                "root_id": str(root.id.uuid),
                "revision": root.revision,
            },
        )
        return root

    async def save(self, root: CatalogItem) -> None:
        """Сохраняет доменное изменение; commit остаётся у внешнего UoW."""
        await self._repository.save(root)
        logger.debug(
            "Catalog mutation prepared for external commit",
            extra={
                "event": "catalog.mutation.prepared",
                "root_id": str(root.id.uuid),
                "revision": root.revision,
            },
        )
