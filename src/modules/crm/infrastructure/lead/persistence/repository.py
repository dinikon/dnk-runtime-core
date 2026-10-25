from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.domain.lead.aggregate import Lead
from src.modules.crm.infrastructure.persistence.models.lead import LeadModel
from src.modules.crm.infrastructure.lead.persistence.mapper import LeadMapper


class SqlAlchemyLeadRepository:
    """Записывает Lead на сессии внешнего tenant UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию с уже выбранной схемой."""
        self._session = session

    async def get_for_update(self, record_id: EntityIdVO) -> Lead | None:
        """Блокирует владельца до последующего изменения его корзины."""
        row = (
            (
                await self._session.execute(
                    select(LeadModel.__table__)
                    .where(LeadModel.id == record_id.uuid)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return LeadMapper.to_domain(row)

    async def add(self, entity: Lead) -> None:
        """Добавляет корень и внутренние связи без commit."""
        await self._session.execute(
            insert(LeadModel).values(**LeadMapper.to_values(entity))
        )

    async def save(self, entity: Lead) -> None:
        """Сохраняет проверенное доменом состояние без commit."""
        values = LeadMapper.to_values(entity)
        values.pop("id")
        await self._session.execute(
            update(LeadModel).where(LeadModel.id == entity.id.uuid).values(**values)
        )
