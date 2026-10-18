from src.modules.channels.application.port.jobs import ChannelsJobsProtocol
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.channels.infrastructure.sync_run.persistence.query_mapper import (
    SyncRunQueryMapper,
)
from src.modules.channels.application.sync_run.query.get_publication_initialization.query import (
    GetPublicationInitializationQuery,
)
from src.modules.channels.application.sync_run.query.get_publication_initialization.dto import (
    GetPublicationInitializationResultDTO,
)
from src.modules.channels.domain.error import ChannelsNotFoundError


class SqlAlchemySyncRunQueryRepository:
    """Читает последний прогресс отдельно от Channel verification и is_enabled."""

    def __init__(self, session: AsyncSession, jobs: ChannelsJobsProtocol) -> None:
        """Принимает внешнюю tenant-сессию."""
        self.session, self.jobs = (session, jobs)

    async def get_publication_initialization(
        self, query: GetPublicationInitializationQuery
    ) -> GetPublicationInitializationResultDTO:
        """Возвращает not_started только существующего Connection."""
        if (
            await self.session.scalar(
                select(ConnectionModel.id).where(
                    ConnectionModel.id == query.connection_id
                )
            )
            is None
        ):
            raise ChannelsNotFoundError("connection_not_found")
        row = (
            (
                await self.session.execute(
                    select(SyncRunModel.__table__)
                    .where(SyncRunModel.connection_id == query.connection_id)
                    .order_by(SyncRunModel.created_at.desc(), SyncRunModel.id.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        recovery_required = False
        if row and row["status"] in ("queued", "running"):
            recovery_required = not row["job_id"] or not await self.jobs.is_recoverable(
                query.tenant_id, row["job_id"]
            )
        return SyncRunQueryMapper.to_details(
            query.connection_id, row, recovery_required
        )
