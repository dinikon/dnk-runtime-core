from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseDetailsDTO,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.cursor import (
    WarehouseListCursor,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.dto import (
    ListWarehouseItemDTO,
)
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.domain.warehouse.value_object.status import WarehouseStatus
from src.modules.warehousing.domain.warehouse.value_object.warehouse_type import (
    WarehouseTypeVO,
)
from src.modules.warehousing.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.warehousing.infrastructure.warehouse.persistence.query_mapper import (
    WarehouseQueryMapper,
)


class SqlAlchemyWarehouseQueryRepository:
    """Читает проекции в выбранной tenant-схеме без восстановления агрегата."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую session внешнего UoW."""
        self._session = session

    async def get_details(
        self,
        *,
        tenant_id: EntityIdVO,
        warehouse_id: WarehouseIdVO,
    ) -> GetWarehouseDetailsDTO | None:
        """Читает карточку одним запросом либо возвращает None."""
        table = WarehouseModel.__table__
        result = await self._session.execute(
            select(table).where(table.c.id == warehouse_id.uuid)
        )
        row = result.mappings().one_or_none()
        return None if row is None else WarehouseQueryMapper.to_details(row)

    async def list_items(
        self,
        *,
        tenant_id: EntityIdVO,
        status: WarehouseStatus | None,
        warehouse_type: WarehouseTypeVO | None,
        cursor: WarehouseListCursor | None,
        limit: int,
    ) -> tuple[ListWarehouseItemDTO, ...]:
        """Читает ограниченную страницу по code/UUID с явными фильтрами."""
        table = WarehouseModel.__table__
        statement = select(
            table.c.id,
            table.c.code,
            table.c.title,
            table.c.type,
            table.c.status,
            table.c.revision,
        )
        if status is not None:
            statement = statement.where(table.c.status == status.value)
        if warehouse_type is not None:
            statement = statement.where(table.c.type == warehouse_type.value)
        if cursor is not None:
            statement = statement.where(
                tuple_(table.c.code, table.c.id)
                > tuple_(cursor.code, cursor.warehouse_id)
            )
        result = await self._session.execute(
            statement.order_by(table.c.code, table.c.id).limit(limit)
        )
        return tuple(
            WarehouseQueryMapper.to_list_item(row) for row in result.mappings()
        )
