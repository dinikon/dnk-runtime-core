from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.application.port.position_history import PositionHistoryEntry
from src.modules.crm.domain.value_object.stage_snapshot import StageSnapshot
from src.modules.crm.infrastructure.persistence.models.position_history import (
    PositionHistoryModel,
)


class SqlAlchemyPositionHistory:
    """Записывает историю на общей tenant-сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW."""
        self._session = session

    @staticmethod
    def _snapshot(value: StageSnapshot | None) -> dict[str, str] | None:
        """Преобразует собственный снимок в JSON без внешних чтений."""
        if value is None:
            return None
        return dict(
            funnel_id=str(value.funnel_id.uuid),
            stage_id=str(value.stage_id.uuid),
            funnel_name=value.funnel_name,
            stage_name=value.stage_name,
            kind=value.kind,
        )

    async def append(self, entry: PositionHistoryEntry) -> None:
        """Добавляет факт без commit и без FK к определению Funnel."""
        await self._session.execute(
            insert(PositionHistoryModel).values(
                id=entry.id,
                model_key=entry.model_key,
                record_id=entry.record_id,
                previous=self._snapshot(entry.previous),
                current=self._snapshot(entry.current),
                previous_revision=entry.previous_revision,
                current_revision=entry.current_revision,
                reason=entry.reason,
                actor_id=entry.actor_id,
                occurred_at=entry.occurred_at,
            )
        )
