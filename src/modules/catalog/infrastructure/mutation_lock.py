from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class PostgresCatalogMutationLock:
    """Сериализует изменения отдельных товаров в транзакции внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую сессию без владения транзакцией."""
        self._session = session

    async def acquire_item(
        self, tenant_id: EntityIdVO, item_id: CatalogItemIdVO
    ) -> None:
        """Сериализует команды только одного товара."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"catalog:family:{tenant_id}:{item_id}"},
        )
