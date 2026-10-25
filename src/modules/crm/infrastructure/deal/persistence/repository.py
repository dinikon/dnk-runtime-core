from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.domain.deal.aggregate import Deal
from src.modules.crm.infrastructure.persistence.models.deal import DealModel
from src.modules.crm.infrastructure.deal.persistence.mapper import DealMapper
from src.modules.crm.infrastructure.persistence.models.deal_contact import (
    DealContactModel,
)
from src.modules.crm.infrastructure.persistence.models.deal_company import (
    DealCompanyModel,
)


class SqlAlchemyDealRepository:
    """Записывает Deal на сессии внешнего tenant UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию с уже выбранной схемой."""
        self._session = session

    async def get_for_update(self, record_id: EntityIdVO) -> Deal | None:
        """Блокирует владельца до последующего изменения его корзины."""
        row = (
            (
                await self._session.execute(
                    select(DealModel.__table__)
                    .where(DealModel.id == record_id.uuid)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return DealMapper.to_domain(row, **await self._participants(record_id.uuid))

    async def add(self, entity: Deal) -> None:
        """Добавляет корень и внутренние связи без commit."""
        await self._session.execute(
            insert(DealModel).values(**DealMapper.to_values(entity))
        )
        await self._save_participants(entity)

    async def save(self, entity: Deal) -> None:
        """Сохраняет проверенное доменом состояние без commit."""
        values = DealMapper.to_values(entity)
        values.pop("id")
        await self._session.execute(
            update(DealModel).where(DealModel.id == entity.id.uuid).values(**values)
        )
        await self._save_participants(entity)

    async def _participants(self, record_id: UUID) -> dict[str, tuple[UUID, ...]]:
        """Читает идентификаторы участников без загрузки чужих агрегатов."""
        contacts = (
            (
                await self._session.execute(
                    select(DealContactModel.contact_id)
                    .where(DealContactModel.deal_id == record_id)
                    .order_by(DealContactModel.contact_id)
                )
            )
            .scalars()
            .all()
        )
        companies = (
            (
                await self._session.execute(
                    select(DealCompanyModel.company_id)
                    .where(DealCompanyModel.deal_id == record_id)
                    .order_by(DealCompanyModel.company_id)
                )
            )
            .scalars()
            .all()
        )
        return {"contact_ids": tuple(contacts), "company_ids": tuple(companies)}

    async def _save_participants(self, entity: Deal) -> None:
        """Обновляет внутренние связи в общей транзакции."""
        for model, field, ids in (
            (DealContactModel, "contact_id", entity.contact_ids),
            (DealCompanyModel, "company_id", entity.company_ids),
        ):
            await self._session.execute(
                delete(model).where(model.deal_id == entity.id.uuid)
            )
            if ids:
                await self._session.execute(
                    insert(model),
                    [{"deal_id": entity.id.uuid, field: i.uuid} for i in ids],
                )
