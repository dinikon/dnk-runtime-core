from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.domain.basket.aggregate import Basket
from src.modules.crm.infrastructure.persistence.models.basket import BasketModel
from src.modules.crm.infrastructure.persistence.models.basket_item import (
    BasketItemModel,
)
from src.modules.crm.infrastructure.basket.persistence.mapper import BasketMapper


class SqlAlchemyBasketRepository:
    """Записывает весь Basket в общей транзакции владельца."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию UoW."""
        self._session = session

    async def get_owner_for_update(
        self, model_key: str, owner_id: EntityIdVO
    ) -> Basket | None:
        """Блокирует корзину после блокировки её владельца."""
        row = (
            (
                await self._session.execute(
                    select(BasketModel.__table__)
                    .where(
                        BasketModel.owner_model_key == model_key,
                        BasketModel.owner_record_id == owner_id.uuid,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        items = (
            (
                await self._session.execute(
                    select(BasketItemModel.__table__)
                    .where(BasketItemModel.basket_id == row["id"])
                    .order_by(BasketItemModel.position)
                )
            )
            .mappings()
            .all()
        )
        return BasketMapper.to_domain(row, list(items))

    async def _items(self, entity: Basket) -> None:
        """Сохраняет внутренние строки целиком, без отдельных репозиториев."""
        await self._session.execute(
            delete(BasketItemModel).where(BasketItemModel.basket_id == entity.id.uuid)
        )
        if entity.items:
            await self._session.execute(
                insert(BasketItemModel),
                [
                    dict(
                        id=i.id.uuid,
                        basket_id=entity.id.uuid,
                        position=p,
                        name=i.name,
                        kind=i.kind,
                        catalog_item_id=(
                            i.catalog_item_id.uuid if i.catalog_item_id else None
                        ),
                        sku=i.sku,
                        quantity=i.quantity,
                        unit=i.unit,
                        unit_price=i.unit_price,
                        line_total=i.total,
                        custom_fields=i.custom_fields,
                    )
                    for p, i in enumerate(entity.items)
                ],
            )

    async def add(self, entity: Basket) -> None:
        """Добавляет корзину без commit."""
        await self._session.execute(
            insert(BasketModel).values(**BasketMapper.to_values(entity))
        )
        await self._items(entity)

    async def save(self, entity: Basket) -> None:
        """Сохраняет агрегат без commit."""
        values = BasketMapper.to_values(entity)
        values.pop("id")
        await self._session.execute(
            update(BasketModel).where(BasketModel.id == entity.id.uuid).values(**values)
        )
        await self._items(entity)
