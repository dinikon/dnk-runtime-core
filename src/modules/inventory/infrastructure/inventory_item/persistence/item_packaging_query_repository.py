from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.application.inventory_item.query.get_item_packaging.query import (
    GetItemPackagingQuery,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.dto import (
    GetItemPackagingResultDTO,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.query import (
    ListItemPackagingsQuery,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.dto import (
    ListItemPackagingsResultDTO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.item_packaging_query_mapper import (
    ItemPackagingQueryMapper,
)
from src.modules.inventory.infrastructure.persistence.models.item_packaging import (
    ItemPackagingModel,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)


class SqlAlchemyItemPackagingQueryRepository:
    """Читает проекции упаковок только в текущем tenant и указанном товаре."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию общего UoW без выбора схемы и управления транзакцией."""
        self._session = session

    async def item_exists(self, identifier: InventoryItemIdVO) -> bool:
        """Проверяет наличие корня без восстановления его Domain-состояния."""
        statement = select(InventoryItemModel.id).where(
            InventoryItemModel.id == identifier.uuid
        )
        return await self._session.scalar(statement) is not None

    async def get_details(
        self, query: GetItemPackagingQuery
    ) -> GetItemPackagingResultDTO | None:
        """Ищет упаковку по паре идентификаторов и перечитывает identity map."""
        statement = (
            select(ItemPackagingModel)
            .where(
                ItemPackagingModel.inventory_item_id == query.inventory_item_id.uuid,
                ItemPackagingModel.id == query.packaging_id.uuid,
            )
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return ItemPackagingQueryMapper.to_details(model) if model is not None else None

    async def list(self, query: ListItemPackagingsQuery) -> ListItemPackagingsResultDTO:
        """Использует одинаковые фильтры страницы и total и сохранённый порядок детей."""
        filters: tuple[ColumnElement[bool], ...] = (
            ItemPackagingModel.inventory_item_id == query.inventory_item_id.uuid,
        )
        if query.search is not None:
            filters += (
                or_(
                    func.lower(ItemPackagingModel.code.collate("default")).contains(
                        query.search.lower(), autoescape=True
                    ),
                    func.lower(ItemPackagingModel.name).contains(
                        query.search.lower(), autoescape=True
                    ),
                ),
            )
        total = await self._session.execute(
            select(func.count()).select_from(ItemPackagingModel).where(*filters)
        )
        statement = (
            select(ItemPackagingModel)
            .where(*filters)
            .order_by(ItemPackagingModel.position, ItemPackagingModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        models = (await self._session.scalars(statement)).all()
        return ListItemPackagingsResultDTO(
            items=tuple(
                ItemPackagingQueryMapper.to_list_item(model) for model in models
            ),
            total=total.scalar_one(),
            offset=query.offset,
            limit=query.limit,
        )
