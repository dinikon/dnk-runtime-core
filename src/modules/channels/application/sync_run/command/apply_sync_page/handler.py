"""Атомарное применение снимков, checkpoint и следующего задания."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from src.modules.channels.application.sync_run.command.apply_sync_page.command import (
    ApplySyncPageCommand,
)
from src.modules.channels.application.sync_run.port.jobs import (
    PublicationSyncJobs,
    SyncJob,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.sync_run.repository import SyncRunRepositoryProtocol
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
    PublicationStructurePolicy,
)
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)
from src.modules.channels.domain.external_publication.repository import (
    ExternalPublicationRepositoryProtocol,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)


class ApplySyncPageHandler:
    """Не выполняет сетевых операций и не коммитит транзакцию самостоятельно."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        runs: SyncRunRepositoryProtocol,
        publications: ExternalPublicationRepositoryProtocol,
        jobs: PublicationSyncJobs,
        clock: Callable[[], datetime],
        uuid: Callable[[], UUID],
    ) -> None:
        """Получает порты одной внешней транзакции."""
        (
            self.channels,
            self.runs,
            self.publications,
            self.jobs,
            self.clock,
            self.uuid,
        ) = (channels, runs, publications, jobs, clock, uuid)

    async def execute(self, command: ApplySyncPageCommand) -> None:
        """Игнорирует устаревший результат до изменения каких-либо снимков."""
        job = command.job
        channel = await self.channels.get(
            EntityIdVO.from_value(job.channel_id), for_update=True
        )
        if (
            channel is None
            or channel.connection.id.uuid != job.connection_id
            or channel.connection.config_revision != job.config_revision
        ):
            return
        run = await self.runs.get(EntityIdVO.from_value(job.run_id))
        if (
            run is None
            or run.connection_id.uuid != job.connection_id
            or not run.accepts(
                job_id=EntityIdVO.from_value(job.job_id),
                config_revision=job.config_revision,
                revision=command.expected_revision,
            )
        ):
            return
        if not await self.jobs.owns(job, command.lock_token, for_update=True):
            return
        now = self.clock()
        if command.error_code is not None:
            run.fail(error_code=command.error_code, now=now)
            await self.runs.save(run)
            return
        page = command.page
        if page is None:
            raise InvalidExternalPublicationError("Результат страницы отсутствует.")
        observations = {item.key: item for item in (*page.items, *page.dependencies)}
        keys = set(observations)
        keys.update(
            (item.parent_resource_type, item.parent_external_id)
            for item in observations.values()
            if item.parent_external_id is not None
        )
        existing = await self.publications.by_keys(
            EntityIdVO.from_value(job.connection_id), tuple(keys)
        )
        by_key = {(item.resource_type, item.external_id): item for item in existing}
        ids = {
            key: by_key[key].id if key in by_key else EntityIdVO.from_value(self.uuid())
            for key in observations
        }
        ids.update({key: item.id for key, item in by_key.items()})
        changed = []
        for key, observation in observations.items():
            parent_id = None
            if observation.parent_external_id is not None:
                parent_id = ids.get(
                    (observation.parent_resource_type, observation.parent_external_id)
                )
                if parent_id is None:
                    raise InvalidExternalPublicationError("Основной товар не получен.")
            values = dict(
                kind=observation.kind,
                parent_id=parent_id,
                raw_data=observation.raw_data,
                data=observation.data,
                platform_schema=observation.platform_schema,
                platform_data=observation.platform_data,
                run_id=run.id,
                now=now,
            )
            publication = by_key.get(key)
            if publication is None:
                publication = ExternalPublication.create(
                    publication_id=ids[key],
                    connection_id=EntityIdVO.from_value(job.connection_id),
                    resource_type=key[0],
                    external_id=key[1],
                    **values,
                )
            else:
                publication.observe(**values)
            changed.append(publication)
        affected = await self.publications.affected_tree(
            EntityIdVO.from_value(job.connection_id), tuple(ids.values())
        )
        final_tree = {item.id: item for item in (*affected, *existing, *changed)}
        PublicationStructurePolicy().ensure_valid(
            tuple(final_tree.values()), required_parent_kind=command.parent_kind
        )
        next_job = None if page.done else self.uuid()
        run.apply_page(
            checkpoint=page.checkpoint.to_document(),
            processed=page.processed_count,
            skipped=page.skipped_count,
            next_job_id=EntityIdVO.from_value(next_job) if next_job else None,
            now=now,
        )
        await self.runs.save(run)
        for publication in sorted(changed, key=lambda item: item.parent_id is not None):
            await self.publications.save(publication)
        if next_job is not None:
            await self.jobs.schedule(
                SyncJob(
                    job.tenant_id,
                    job.channel_id,
                    job.connection_id,
                    job.run_id,
                    next_job,
                    job.config_revision,
                ),
                now,
            )
        if not await self.jobs.owns(job, command.lock_token):
            raise ScheduledJobDeferred("Publication lease expired before commit")
