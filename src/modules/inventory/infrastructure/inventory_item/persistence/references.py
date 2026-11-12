from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.inventory_item.port.references import (
    InventoryItemReferenceDTO,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)


class SqlAlchemyInventoryItemReferences:
    """Читает публичные проекции SKU на общей tenant-сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Не открывает новую транзакцию и не выбирает tenant-схему."""
        self._session = session

    async def find(self, sku: str) -> InventoryItemReferenceDTO | None:
        """Читает точное каноническое совпадение без изменения позиции."""
        table = InventoryItemModel.__table__
        row = (
            await self._session.execute(
                select(table.c.id, table.c.sku).where(table.c.sku == sku)
            )
        ).one_or_none()
        return InventoryItemReferenceDTO(row.id, row.sku) if row else None

    async def read(
        self, identifiers: tuple[UUID, ...]
    ) -> tuple[InventoryItemReferenceDTO, ...]:
        """Читает коды для проекции потребителя одним запросом."""
        if not identifiers:
            return ()
        table = InventoryItemModel.__table__
        rows = (
            await self._session.execute(
                select(table.c.id, table.c.sku).where(table.c.id.in_(identifiers))
            )
        ).all()
        return tuple(InventoryItemReferenceDTO(row.id, row.sku) for row in rows)

    async def search_ids(self, search: str) -> tuple[UUID, ...]:
        """Возвращает полный набор ID для последующей серверной фильтрации Catalog."""
        table = InventoryItemModel.__table__
        return tuple(
            (
                await self._session.scalars(
                    select(table.c.id).where(
                        table.c.sku.contains(search, autoescape=True)
                    )
                )
            ).all()
        )
