"""Координация запуска и отмены на уже открытом UoW."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.sync_run.aggregate import SyncRun
from src.modules.channels.domain.sync_run.repository import SyncRunRepositoryProtocol
from src.modules.channels.application.sync_run.port.jobs import (
    PublicationSyncJobs,
    SyncJob,
)


class SyncRuns:
    """Сериализуется вызывающим сценарием через блокировку Channel."""

    def __init__(
        self,
        runs: SyncRunRepositoryProtocol,
        jobs: PublicationSyncJobs,
        clock: Callable[[], datetime],
        uuid: Callable[[], UUID],
    ) -> None:
        """Принимает порты общей транзакции без session и открытия UoW."""
        self.runs, self.jobs, self.clock, self.uuid = runs, jobs, clock, uuid

    async def start(
        self, *, channel: Channel, tenant_id: UUID, automatic: bool
    ) -> SyncRun | None:
        """Возвращает действующий запуск либо создаёт новое поколение обхода."""
        channel.require_verified_connection()
        connection = channel.connection
        current = await self.runs.active(connection.id)
        if current is not None:
            if (
                current.config_revision == connection.config_revision
                and await self.jobs.active(tenant_id, current.current_job_id.uuid)
            ):
                return current
            current.fail(error_code="sync_interrupted", now=self.clock())
            await self.runs.save(current)
            await self.jobs.cancel(tenant_id, current.id.uuid, self.clock())
        if automatic and await self.runs.automatic_exists(
            connection.id, connection.config_revision
        ):
            return None
        now, job_id = self.clock(), self.uuid()
        run = SyncRun.create(
            run_id=EntityIdVO.from_value(self.uuid()),
            connection_id=connection.id,
            config_revision=connection.config_revision,
            job_id=EntityIdVO.from_value(job_id),
            automatic=automatic,
            now=now,
        )
        await self.runs.save(run)
        await self.jobs.schedule(
            SyncJob(
                tenant_id,
                channel.id.uuid,
                connection.id.uuid,
                run.id.uuid,
                job_id,
                connection.config_revision,
            ),
            now,
        )
        return run

    async def cancel(self, *, channel: Channel, tenant_id: UUID, reason: str) -> None:
        """Отменяет запуск перед заменой доступа либо удалением Channel."""
        run = await self.runs.active(channel.connection.id)
        if run is not None:
            run.cancel(error_code=reason, now=self.clock())
            await self.runs.save(run)
            await self.jobs.cancel(tenant_id, run.id.uuid, self.clock())
