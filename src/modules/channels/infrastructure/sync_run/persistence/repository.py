"""SQL-адаптер агрегата SyncRun на общей сессии UoW."""

from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.sync_run.aggregate import SyncRun
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.channels.infrastructure.sync_run.persistence.mapper import (
    to_domain,
    to_values,
)


class SqlAlchemySyncRunRepository:
    """Сохраняет запуски, не определяя политику конкурентного старта."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего UoW."""
        self.session = session

    async def get(self, run_id: EntityIdVO) -> SyncRun | None:
        """Восстанавливает один запуск."""
        row = await self.session.scalar(
            select(SyncRunModel).where(SyncRunModel.id == run_id.uuid)
        )
        return to_domain(row) if row is not None else None

    async def active(self, connection_id: EntityIdVO) -> SyncRun | None:
        """Читает активный запуск после блокировки Channel вызывающим сценарием."""
        row = await self.session.scalar(
            select(SyncRunModel)
            .where(
                SyncRunModel.connection_id == connection_id.uuid,
                SyncRunModel.status.in_(("queued", "running")),
            )
            .order_by(SyncRunModel.created_at.desc(), SyncRunModel.id.desc())
        )
        return to_domain(row) if row is not None else None

    async def automatic_exists(
        self, connection_id: EntityIdVO, config_revision: int
    ) -> bool:
        """Проверяет предыдущий автоматический старт данного поколения доступа."""
        return (
            await self.session.scalar(
                select(SyncRunModel.id)
                .where(
                    SyncRunModel.connection_id == connection_id.uuid,
                    SyncRunModel.config_revision == config_revision,
                    SyncRunModel.automatic.is_(True),
                )
                .limit(1)
            )
            is not None
        )

    async def save(self, run: SyncRun) -> None:
        """Сохраняет готовые значения, не открывая свою транзакцию."""
        table = SyncRunModel.__table__
        values = to_values(run)
        result = await self.session.execute(
            update(table).where(table.c.id == run.id.uuid).values(**values)
        )
        if result.rowcount == 0:
            await self.session.execute(insert(table).values(**values))
