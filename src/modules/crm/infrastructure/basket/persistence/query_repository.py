from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.application.basket.values import (
    OwnerBasketProjection,
    BasketItemProjection,
    BasketSummaryProjection,
)
from src.modules.crm.infrastructure.persistence.models.basket import BasketModel
from src.modules.crm.infrastructure.persistence.models.basket_item import (
    BasketItemModel,
)


class SqlAlchemyBasketQueryRepository:
    """Читает денежные проекции без восстановления Domain Basket."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию текущего UoW."""
        self._session = session

    async def get_owner(
        self, model_key: str, owner_id: UUID
    ) -> OwnerBasketProjection | None:
        """Читает заголовок и строки одним SQL snapshot."""
        fields = (
            "id",
            "name",
            "kind",
            "quantity",
            "unit_price",
            "line_total",
            "unit",
            "catalog_item_id",
            "sku",
            "custom_fields",
        )
        stmt = (
            select(
                BasketModel.__table__,
                *(getattr(BasketItemModel, k).label("item_" + k) for k in fields),
            )
            .outerjoin(BasketItemModel, BasketItemModel.basket_id == BasketModel.id)
            .where(
                BasketModel.owner_model_key == model_key,
                BasketModel.owner_record_id == owner_id,
            )
            .order_by(BasketItemModel.position)
        )
        rows = (await self._session.execute(stmt)).mappings().all()
        if not rows:
            return None
        row = rows[0]
        items = []
        for r in rows:
            if r["item_id"] is not None:
                values = {k: r["item_" + k] for k in fields}
                for k in ("quantity", "unit_price", "line_total"):
                    values[k] = str(values[k])
                items.append(BasketItemProjection(**values))
        return OwnerBasketProjection(
            row["id"],
            row["currency"],
            row["revision"],
            row["state"],
            str(row["total"]),
            tuple(items),
        )

    async def summaries(
        self, model_key: str, owner_ids: tuple[UUID, ...]
    ) -> dict[UUID, BasketSummaryProjection]:
        """Пакетно читает итоги канбана, без N+1."""
        rows = (
            (
                await self._session.execute(
                    select(
                        BasketModel.owner_record_id,
                        BasketModel.currency,
                        BasketModel.total,
                        BasketModel.revision,
                    ).where(
                        BasketModel.owner_model_key == model_key,
                        BasketModel.owner_record_id.in_(owner_ids),
                    )
                )
            ).all()
            if owner_ids
            else []
        )
        return {r[0]: BasketSummaryProjection(r[1], str(r[2]), r[3]) for r in rows}
