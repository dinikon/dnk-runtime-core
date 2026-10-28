from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.infrastructure.persistence.models.deal import DealModel
from src.modules.crm.infrastructure.persistence.models.lead import LeadModel


class SqlAlchemyFunnelUsageQuery:
    """Читает собственные таблицы CRM для публичного Application-контракта."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW."""
        self._session = session

    async def counts(self, model_key: str, funnel_id: UUID) -> dict[UUID, int]:
        """Группирует карточки одной воронки одним запросом."""
        model = LeadModel if model_key == "crm.lead" else DealModel
        return dict(
            (
                await self._session.execute(
                    select(model.stage_id, func.count())
                    .where(
                        model.funnel_id == funnel_id,
                    )
                    .group_by(model.stage_id)
                )
            ).all()
        )
