from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source import (
    SupplierSourceModel,
)


class SqlAlchemySupplierSourceUsage:
    """Реализует публичную проверку использования на общей tenant-сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW."""
        self._session = session

    async def is_supplier_used(self, model_key: str, supplier_id: UUID) -> bool:
        """Читает существование ссылки без загрузки агрегатов."""
        statement = select(
            select(SupplierSourceModel.id)
            .where(
                SupplierSourceModel.supplier_model_key == model_key,
                SupplierSourceModel.supplier_id == supplier_id,
            )
            .exists()
        )
        return (await self._session.execute(statement)).scalar_one()
