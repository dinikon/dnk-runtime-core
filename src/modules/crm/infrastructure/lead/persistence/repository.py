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

    async def get(self, record_id: EntityIdVO) -> Lead | None:
        """Восстанавливает агрегат для предварительного решения о блокировках."""
        row = (
            (
                await self._session.execute(
                    select(LeadModel.__table__).where(LeadModel.id == record_id.uuid)
                )
            )
            .mappings()
            .one_or_none()
        )
        return LeadMapper.to_domain(row) if row is not None else None

    async def list_in_stages_for_update(
        self, funnel_id: EntityIdVO, stage_ids: tuple[EntityIdVO, ...]
    ) -> tuple[Lead, ...]:
        """Получает агрегаты в стабильном порядке на сессии внешнего UoW."""
        ids = (
            (
                await self._session.execute(
                    select(LeadModel.id)
                    .where(
                        LeadModel.funnel_id == funnel_id.uuid,
                        LeadModel.stage_id.in_([value.uuid for value in stage_ids]),
                    )
                    .order_by(LeadModel.id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        entities = []
        for record_id in ids:
            entity = await self.get_for_update(EntityIdVO(record_id))
            if entity is not None:
                entities.append(entity)
        return tuple(entities)
