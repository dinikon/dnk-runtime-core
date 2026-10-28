from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.query import (
    GetCatalogProductSnapshotQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.dto import (
    GetCatalogProductSnapshotResultDTO,
)
from src.modules.catalog.application.catalog_item.port.query_repository import (
    CatalogItemQueryRepositoryProtocol,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.shared.domain.time.clock_port import ClockPort


class GetCatalogProductSnapshotHandler:
    """Читает конкретную проекцию через Application-порт без Aggregate restore."""

    def __init__(
        self,
        repository: CatalogItemQueryRepositoryProtocol,
        clock: ClockPort,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает read порт и часы согласованного as_of."""
        self._repository, self._clock, self._lock = repository, clock, lock

    async def execute(
        self, query: GetCatalogProductSnapshotQuery
    ) -> GetCatalogProductSnapshotResultDTO:
        """Проверяет locale и возвращает результат конкретного сценария."""
        LocaleVO(query.locale)
        await self._lock.acquire_item(query.tenant_id, query.item_id)
        return await self._repository.get_snapshot(
            query, query.as_of or self._clock.now()
        )
