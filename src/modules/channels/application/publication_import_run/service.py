from datetime import datetime
from src.modules.channels.domain.publication_import_run.value_object.identifier import (
    PublicationImportRunIdVO,
)
from uuid import UUID
from src.modules.channels.application.publication_import_run.error import (
    PublicationImportUnavailableError,
)
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.application.channel.port.registry import ChannelRegistryPort
from src.modules.channels.domain.publication_import_run.aggregate import (
    PublicationImportRun,
)
from src.modules.channels.domain.publication_import_run.repository import (
    PublicationImportRunRepositoryProtocol,
)
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob

JOB_TYPE = "channels.publication_import"


class PublicationImportStarter:
    """Общий запуск для создания канала и ручного обновления публикаций."""

    def __init__(
        self,
        runs: PublicationImportRunRepositoryProtocol,
        jobs: ScheduledJobRepositoryProtocol,
        uuids: UUIdGeneratorProtocol,
        registry: ChannelRegistryPort,
    ) -> None:
        """Принимает порты одной транзакции и генератор идентификаторов."""
        self._runs, self._jobs, self._uuids = runs, jobs, uuids
        self._registry = registry

    async def start(
        self, *, channel: Channel, tenant_id: UUID, now: datetime
    ) -> PublicationImportRun:
        """Возвращает активный запуск или атомарно создаёт новый с заданием."""
        if (
            not channel.is_active
            or not self._registry.get(channel.kind.value).reads_publications
        ):
            raise PublicationImportUnavailableError(
                "Импорт доступен для активных каналов с поддержкой чтения публикаций."
            )
        active = await self._runs.active(channel.id)
        if active is not None:
            terminal = await self._jobs.terminal_or_missing(
                tenant_id=tenant_id, job_ids=[active.job_id.uuid]
            )
            if (
                active.connection_revision == channel.connection_revision
                and active.job_id.uuid not in terminal
            ):
                return active
            await self._runs.save(
                active.finish(
                    error_code=(
                        "connection_changed"
                        if active.connection_revision != channel.connection_revision
                        else "worker_exhausted"
                    ),
                    now=now,
                )
            )
        run = PublicationImportRun.create(
            id=PublicationImportRunIdVO.from_value(self._uuids.new()),
            channel_id=channel.id,
            connection_revision=channel.connection_revision,
            now=now,
        )
        await self._runs.save(run)
        await schedule_import_page(self._jobs, run, tenant_id, now)
        return run


async def schedule_import_page(
    jobs: ScheduledJobRepositoryProtocol,
    run: PublicationImportRun,
    tenant_id: UUID,
    now: datetime,
) -> None:
    """Сохраняет детерминированное задание в транзакции страницы или запуска."""
    await jobs.schedule_once(
        ScheduledJob(
            id=run.job_id.uuid,
            tenant_id=tenant_id,
            job_type=JOB_TYPE,
            payload={"channel_id": str(run.channel_id), "run_id": str(run.id)},
            run_at=now,
            status="scheduled",
            attempts=0,
            locked_until=None,
            lock_token=None,
            created_at=now,
            updated_at=now,
        )
    )
