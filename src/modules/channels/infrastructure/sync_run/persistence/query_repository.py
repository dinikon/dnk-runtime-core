"""Read-side состояния запусков без их checkpoint."""

from uuid import UUID

from sqlalchemy import select, Select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.application.sync_run.port.query_repository import (
    SyncRunReadRow,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel


class SqlAlchemySyncRunQueryRepository:
    """Не восстанавливает агрегат ради отображения прогресса."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую tenant-сессию."""
        self.session = session

    def _statement(self) -> Select:
        """Выбирает только публичные поля и ID задания для проверки recovery."""
        r = SyncRunModel
        return select(
            r.id,
            r.config_revision,
            r.revision,
            r.status,
            r.processed_count,
            r.skipped_count,
            r.pages_count,
            r.automatic,
            r.error_code,
            r.created_at,
            r.started_at,
            r.finished_at,
            r.current_job_id,
        )

    async def latest(self, connection_id: UUID) -> SyncRunReadRow | None:
        """Сортирует по времени и UUID для детерминированного результата."""
        r = SyncRunModel
        row = (
            await self.session.execute(
                self._statement()
                .where(r.connection_id == connection_id)
                .order_by(r.created_at.desc(), r.id.desc())
                .limit(1)
            )
        ).one_or_none()
        return to_read_row(row) if row else None

    async def get(self, connection_id: UUID, run_id: UUID) -> SyncRunReadRow | None:
        """Не раскрывает запуски другого подключения."""
        r = SyncRunModel
        row = (
            await self.session.execute(
                self._statement().where(
                    r.connection_id == connection_id, r.id == run_id
                )
            )
        ).one_or_none()
        return to_read_row(row) if row else None


def to_read_row(row: Row) -> SyncRunReadRow:
    """Перечисляет безопасные поля проекции явно."""
    return SyncRunReadRow(
        row.id,
        row.config_revision,
        row.revision,
        row.status,
        row.processed_count,
        row.skipped_count,
        row.pages_count,
        row.automatic,
        row.error_code,
        row.created_at,
        row.started_at,
        row.finished_at,
        row.current_job_id,
    )
