from sqlalchemy import select
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.sku.query.get_sku.dto import SkuDetailsDTO
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO
from src.modules.inventory.infrastructure.persistence.models.sku import SkuModel
from src.modules.inventory.infrastructure.sku.persistence.query_mapper import (
    SkuQueryMapper,
)


class SqlAlchemySkuQueryRepository:
    """Read side использует схему tenant, привязанную к сессии внешним UoW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _details_select():
        return select(
            SkuModel.id.label("id"),
            SkuModel.code.label("code"),
            SkuModel.title.label("title"),
            SkuModel.created_at.label("created_at"),
            SkuModel.updated_at.label("updated_at"),
            SkuModel.created_by.label("created_by"),
            SkuModel.updated_by.label("updated_by"),
        )

    async def get_details(self, *, sku_id: SkuIdVO) -> SkuDetailsDTO | None:
        """Возвращает одну проекцию без блокировки агрегата."""
        result = await self._session.execute(
            self._details_select().where(SkuModel.id == sku_id.uuid)
        )
        row = result.mappings().one_or_none()
        return None if row is None else SkuQueryMapper.to_details(row)

    async def list_details(self, *, limit: int, offset: int) -> list[SkuDetailsDTO]:
        """Читает страницу с устойчивым порядком по коду и ID."""
        result = await self._session.execute(
            self._details_select()
            .order_by(SkuModel.code, SkuModel.id)
            .limit(limit)
            .offset(offset)
        )
        return [SkuQueryMapper.to_details(row) for row in result.mappings().all()]

    async def get_codes(self, *, sku_ids: tuple[UUID, ...]) -> dict[UUID, str]:
        if not sku_ids:
            return {}
        rows = (
            await self._session.execute(
                select(SkuModel.id, SkuModel.code).where(SkuModel.id.in_(sku_ids))
            )
        ).all()
        return {row.id: row.code for row in rows}
