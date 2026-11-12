from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.warehouse.query.get_warehouse.query import (
    GetWarehouseQuery,
)
from src.modules.inventory.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseResultDTO,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.dto import (
    ListWarehousesResultDTO,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.inventory.infrastructure.warehouse.persistence.query_mapper import (
    WarehouseQueryMapper,
)


class SqlAlchemyWarehouseQueryRepository:
    """Читает типизированные проекции текущей tenant-схемы."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW с выбранной схемой."""
        self._session = session

    async def get_details(
        self, query: GetWarehouseQuery
    ) -> GetWarehouseResultDTO | None:
        """Читает актуальную карточку одним SELECT без восстановления Domain."""
        statement = (
            select(WarehouseModel)
            .where(WarehouseModel.id == query.warehouse_id.uuid)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return WarehouseQueryMapper.to_details(model) if model is not None else None

    async def list(self, query: ListWarehousesQuery) -> ListWarehousesResultDTO:
        """Применяет общие фильтры к total и странице со стабильной сортировкой."""
        filters: tuple[ColumnElement[bool], ...] = ()
        if query.search is not None:
            filters += (
                or_(
                    WarehouseModel.code.contains(
                        query.search.casefold(), autoescape=True
                    ),
                    WarehouseModel.name.icontains(query.search, autoescape=True),
                ),
            )
        if query.is_active is not None:
            filters += (WarehouseModel.is_active.is_(query.is_active),)
        total = await self._session.execute(
            select(func.count()).select_from(WarehouseModel).where(*filters)
        )
        statement = (
            select(WarehouseModel)
            .where(*filters)
            .order_by(WarehouseModel.code, WarehouseModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        models = (await self._session.scalars(statement)).all()
        return ListWarehousesResultDTO(
            items=tuple(WarehouseQueryMapper.to_list_item(model) for model in models),
            total=total.scalar_one(),
            offset=query.offset,
            limit=query.limit,
        )
