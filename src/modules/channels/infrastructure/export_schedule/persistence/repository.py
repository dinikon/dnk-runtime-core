from dataclasses import asdict
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.export_schedule.aggregate import ExportSchedule
from src.modules.channels.infrastructure.persistence.models.export_schedule import (
    ExportScheduleModel as S,
)


class SqlAlchemyExportScheduleRepository:
    """Пишет policy в общей транзакции с durable расписанием."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию внешней сборки."""
        self.session = session

    async def get(self, channel_id: UUID) -> ExportSchedule:
        """Восстанавливает policy либо возвращает выключенный default."""
        row = (
            (
                await self.session.execute(
                    select(S.__table__)
                    .where(S.channel_id == channel_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return (
            ExportSchedule.restore(**row) if row else ExportSchedule.create(channel_id)
        )

    async def save(self, schedule: ExportSchedule) -> None:
        """Сохраняет только состояние Domain без управления транзакцией."""
        values = asdict(schedule)
        await self.session.execute(
            insert(S)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["channel_id"],
                set_={k: v for k, v in values.items() if k != "channel_id"},
            )
        )
