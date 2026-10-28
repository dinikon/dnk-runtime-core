"""Подготовка одного ограниченного шага обхода."""

from collections.abc import Callable
from datetime import datetime

from src.modules.channels.application.sync_run.command.prepare_sync_step.command import (
    PrepareSyncStepCommand,
)
from src.modules.channels.application.sync_run.command.prepare_sync_step.dto import (
    PrepareSyncStepResultDTO,
)
from src.modules.channels.application.sync_run.port.jobs import PublicationSyncJobs
from src.modules.channels.application.sync_run.port.source import (
    PublicationCheckpoint,
    PublicationReadPhase,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.sync_run.repository import SyncRunRepositoryProtocol
from src.modules.channels.domain.external_publication.repository import (
    ExternalPublicationRepositoryProtocol,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PrepareSyncStepHandler:
    """Возвращает доступ только действующему поколению задания."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        runs: SyncRunRepositoryProtocol,
        publications: ExternalPublicationRepositoryProtocol,
        jobs: PublicationSyncJobs,
        clock: Callable[[], datetime],
    ) -> None:
        """Получает порты одной короткой транзакции."""
        self.channels, self.runs, self.publications, self.jobs, self.clock = (
            channels,
            runs,
            publications,
            jobs,
            clock,
        )

    async def execute(
        self, command: PrepareSyncStepCommand
    ) -> PrepareSyncStepResultDTO | None:
        """Подтверждает поколение, начинает запуск и выбирает следующего родителя."""
        job = command.job
        channel = await self.channels.get(
            EntityIdVO.from_value(job.channel_id), for_update=True
        )
        if (
            channel is None
            or channel.connection.id.uuid != job.connection_id
            or channel.connection.config_revision != job.config_revision
        ):
            return None
        run = await self.runs.get(EntityIdVO.from_value(job.run_id))
        if (
            run is None
            or run.connection_id.uuid != job.connection_id
            or not run.accepts(
                job_id=EntityIdVO.from_value(job.job_id),
                config_revision=job.config_revision,
            )
        ):
            return None
        if not await self.jobs.owns(job, command.lock_token, for_update=True):
            return None
        run.start(now=self.clock())
        await self.runs.save(run)
        checkpoint = PublicationCheckpoint.from_document(run.checkpoint)
        parent = None
        if checkpoint.phase is PublicationReadPhase.CHILDREN:
            parent = await self.publications.next_variable_parent(
                EntityIdVO.from_value(job.connection_id),
                run.id,
                checkpoint.after_parent,
                checkpoint.current_parent,
            )
        return PrepareSyncStepResultDTO(
            channel.platform_kind,
            channel.connection.config,
            channel.connection.encrypted_credentials,
            run.revision,
            checkpoint,
            parent,
        )
