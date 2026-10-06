from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.publication_import_run.query.get_publication_import_run.dto import (
    PublicationImportRunDetailsDTO,
)
from src.modules.channels.infrastructure.publication_import_run.persistence.query_mapper import (
    PublicationImportQueryMapper,
)
from src.modules.channels.infrastructure.persistence.models.publication_import_run import (
    PublicationImportRunModel,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)


class SqlAlchemyPublicationImportQueryRepository:
    """Читает прогресс указанного или последнего запуска подключения."""

    def __init__(
        self, session: AsyncSession, jobs: ScheduledJobRepositoryProtocol
    ) -> None:
        """Принимает tenant-сессию и публичный порт shared jobs того же UoW."""
        self._session, self._jobs = session, jobs

    async def get(
        self, tenant_id: UUID, channel_id: UUID, run_id: UUID | None
    ) -> PublicationImportRunDetailsDTO | None:
        """Ограничивает выбор каналу и текущей ревизии подключения."""
        r = PublicationImportRunModel.__table__
        statement = select(
            r.c.id,
            r.c.channel_id,
            r.c.status,
            r.c.job_id,
            r.c.pages,
            r.c.resources,
            r.c.error_code,
            r.c.created_at,
            r.c.updated_at,
        ).join(ChannelModel, ChannelModel.id == r.c.channel_id)
        statement = statement.where(
            r.c.channel_id == channel_id,
            r.c.connection_revision == ChannelModel.connection_revision,
        )
        if run_id is not None:
            statement = statement.where(r.c.id == run_id)
        row = (
            (
                await self._session.execute(
                    statement.order_by(r.c.created_at.desc(), r.c.id.desc()).limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        values = dict(row)
        if row["status"] in ("queued", "running"):
            terminal = await self._jobs.terminal_or_missing(
                tenant_id=tenant_id, job_ids=[row["job_id"]]
            )
            if row["job_id"] in terminal:
                # A page may have committed its continuation between the two reads.
                current = (
                    (
                        await self._session.execute(
                            statement.order_by(
                                r.c.created_at.desc(), r.c.id.desc()
                            ).limit(1)
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if current is None:
                    return None
                values = dict(current)
                if current["job_id"] == row["job_id"] and current["status"] in (
                    "queued",
                    "running",
                ):
                    values["status"] = "partial" if current["resources"] else "failed"
                    values["error_code"] = "worker_exhausted"
        return PublicationImportQueryMapper.to_details(values)
