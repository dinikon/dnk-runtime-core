from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.domain.warehouse.aggregate import Warehouse
from src.modules.warehousing.domain.warehouse.error import (
    WarehouseCodeAlreadyExistsError,
)
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.mapper import (
    WarehouseMapper,
)


class SqlAlchemyWarehouseRepository:
    """Хранит агрегат в общей tenant-сессии без commit и выбора схемы."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает session внешнего UoW, уже привязанную к одному tenant."""
        self._session = session

    async def add(self, *, tenant_id: EntityIdVO, warehouse: Warehouse) -> None:
        """Атомарно вставляет склад; UNIQUE защищает также конкурентный дубликат."""
        table = WarehouseModel.__table__
        result = await self._session.execute(
            insert(table)
            .values(WarehouseMapper.to_insert_values(warehouse))
            .on_conflict_do_nothing(constraint="uq_warehousing_warehouses_code")
            .returning(table.c.id)
        )
        if result.scalar_one_or_none() is None:
            raise WarehouseCodeAlreadyExistsError("Код склада уже существует.")

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        warehouse_id: WarehouseIdVO,
    ) -> Warehouse | None:
        """Читает и восстанавливает агрегат текущего tenant либо возвращает None."""
        table = WarehouseModel.__table__
        result = await self._session.execute(
            select(table).where(table.c.id == warehouse_id.uuid)
        )
        row = result.mappings().one_or_none()
        return None if row is None else WarehouseMapper.to_domain(row)
