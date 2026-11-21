from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.stock_location.query.get_stock_location.query import (
    GetStockLocationQuery,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.dto import (
    GetStockLocationResultDTO,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.query import (
    ListStockLocationsQuery,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.dto import (
    ListStockLocationsResultDTO,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.inventory.infrastructure.stock_location.persistence.query_mapper import (
    StockLocationQueryMapper,
)


class SqlAlchemyStockLocationQueryRepository:
    """Читает плоские проекции локаций в схеме текущего tenant."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию внешнего UoW."""
        self._session = session

    async def warehouse_exists(self, identifier: WarehouseIdVO) -> bool:
        """Проверяет наличие склада без загрузки его агрегата."""
        statement = select(WarehouseModel.id).where(
            WarehouseModel.id == identifier.uuid
        )
        return await self._session.scalar(statement) is not None

    async def get_details(
        self, query: GetStockLocationQuery
    ) -> GetStockLocationResultDTO | None:
        """Ограничивает карточку одновременно ID адреса и ID склада."""
        statement = (
            select(StockLocationModel)
            .where(
                StockLocationModel.id == query.location_id.uuid,
                StockLocationModel.warehouse_id == query.warehouse_id.uuid,
            )
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return StockLocationQueryMapper.to_details(model) if model is not None else None

    async def list(self, query: ListStockLocationsQuery) -> ListStockLocationsResultDTO:
        """Применяет единые фильтры к count и странице со стабильным порядком."""
        filters: tuple[ColumnElement[bool], ...] = (
            StockLocationModel.warehouse_id == query.warehouse_id.uuid,
        )
        if query.search is not None:
            filters += (
                or_(
                    StockLocationModel.code.contains(
                        query.search.casefold(), autoescape=True
                    ),
                    StockLocationModel.name.icontains(query.search, autoescape=True),
                ),
            )
        if query.is_active is not None:
            filters += (StockLocationModel.is_active.is_(query.is_active),)
        if query.location_type is not None:
            filters += (StockLocationModel.location_type == query.location_type.value,)
        if query.parent_location_id is not None:
            filters += (
                StockLocationModel.parent_location_id == query.parent_location_id.uuid,
            )
        total = await self._session.execute(
            select(func.count()).select_from(StockLocationModel).where(*filters)
        )
        statement = (
            select(StockLocationModel)
            .where(*filters)
            .order_by(StockLocationModel.code, StockLocationModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        models = (await self._session.scalars(statement)).all()
        return ListStockLocationsResultDTO(
            items=tuple(
                StockLocationQueryMapper.to_list_item(model) for model in models
            ),
            total=total.scalar_one(),
            offset=query.offset,
            limit=query.limit,
        )
