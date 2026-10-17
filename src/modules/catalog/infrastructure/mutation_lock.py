from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class PostgresCatalogMutationLock:
    """Общий порядок блокировок ссылок и отдельных товаров в transaction UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую сессию без владения транзакцией."""
        self._session = session

    async def acquire(self, tenant_id: EntityIdVO) -> None:
        """Блокирует изменения справочников, совместно используемых товарами."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"catalog:references:{tenant_id}"},
        )

    async def acquire_reference(self, tenant_id: EntityIdVO) -> None:
        """Защищает назначаемые ссылки до завершения внешнего UoW."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock_shared(hashtextextended(:key,0))"),
            {"key": f"catalog:references:{tenant_id}"},
        )

    async def acquire_item(
        self, tenant_id: EntityIdVO, item_id: CatalogItemIdVO
    ) -> None:
        """Сериализует команды только одного товара."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            # Существующий namespace сохраняет совместимость блокировок при выпуске.
            {"key": f"catalog:family:{tenant_id}:{item_id}"},
        )

    async def acquire_read(self, tenant_id: EntityIdVO) -> None:
        """Обычные запросы читают SQL snapshot без advisory блокировки."""
