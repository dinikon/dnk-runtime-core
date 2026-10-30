from datetime import datetime
from uuid import UUID
from src.modules.catalog.application.catalog_item.port.query_repository import (
    CatalogItemQueryRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.dto import (
    GetCatalogProductSnapshotResultDTO,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.query import (
    ListCatalogItemsQuery,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.dto import (
    ListCatalogItemsResultDTO,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogBindingsFacade:
    """Публичные операции владельца Catalog на внешнем tenant UoW."""

    def __init__(
        self, queries: CatalogItemQueryRepositoryProtocol, lock: CatalogMutationLockPort
    ) -> None:
        """Принимает только порты Catalog."""
        self._queries, self._lock = queries, lock

    async def lock(self, tenant_id: UUID, root_id: UUID) -> None:
        """Блокирует семью даже при отсутствии записи для безопасного снятия связи."""
        await self._lock.acquire_item(EntityIdVO(tenant_id), CatalogItemIdVO(root_id))

    async def families(
        self, identifiers: tuple[UUID, ...], locale: str, as_of: datetime
    ) -> tuple[GetCatalogProductSnapshotResultDTO, ...]:
        """Возвращает собственные и эффективные значения одним batch."""
        LocaleVO(locale)
        return await self._queries.snapshots(identifiers, locale, as_of)

    async def families_for_locales(
        self,
        *,
        identifiers: tuple[UUID, ...],
        locales: tuple[str, ...],
        as_of: datetime,
    ) -> tuple[GetCatalogProductSnapshotResultDTO, ...]:
        """Читает все локали batch на одном снимке внешнего UoW.

        Вызывающая сборка обеспечивает REPEATABLE READ до первого SQL-запроса.
        Метод не открывает отдельные транзакции и не выбирает запасную локаль.
        """
        for locale in locales:
            LocaleVO(locale)
        result: list[GetCatalogProductSnapshotResultDTO] = []
        for locale in locales:
            result.extend(await self._queries.snapshots(identifiers, locale, as_of))
        return tuple(result)

    async def search(
        self,
        *,
        tenant_id: UUID,
        kind: str,
        locale: str,
        search: str,
        offset: int,
        limit: int,
        as_of: datetime,
    ) -> ListCatalogItemsResultDTO:
        """Фильтрует тип до пагинации и не исключает архивные карточки."""
        LocaleVO(locale)
        return await self._queries.list(
            ListCatalogItemsQuery(
                tenant_id=EntityIdVO(tenant_id),
                kind=kind,
                locale=locale,
                search=search,
                offset=offset,
                limit=limit,
            ),
            as_of,
        )
