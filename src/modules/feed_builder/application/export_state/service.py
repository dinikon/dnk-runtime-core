from collections.abc import Iterable
from datetime import timedelta
from uuid import UUID

from src.modules.feed_builder.application.export_state.issue import FeedExportIssueDTO
from src.modules.feed_builder.application.export_state.job_types import (
    RETIRE_FILE_JOB_TYPE,
)
from src.modules.feed_builder.application.export_state.port.issue_writer import (
    FeedExportIssueWriterPort,
)
from src.modules.feed_builder.domain.export_state.aggregate import FeedExportState
from src.modules.feed_builder.domain.export_state.enum.export_outcome import (
    ExportOutcome,
)
from src.modules.feed_builder.domain.export_state.policy.publication import (
    publication_rejection_reason,
)
from src.modules.feed_builder.domain.export_state.repository import (
    FeedExportStateRepositoryProtocol,
)
from src.modules.feed_builder.domain.export_state.value_object.active_export import (
    ActiveExportVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_counts import (
    ExportCountsVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_report import (
    ExportReportVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_task import (
    ExportTaskVO,
)
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.feed.value_object.feed_public_link_id import (
    FeedPublicLinkIdVO,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FinishFeedRefreshService:
    """Фиксирует отчёт и замену готового файла в одной транзакции."""

    def __init__(
        self,
        states: FeedExportStateRepositoryProtocol,
        feeds: FeedRepositoryProtocol,
        issues: FeedExportIssueWriterPort,
        schedule: ScheduleScheduledJobUseCase,
        clock: ClockPort,
        ids: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты уже открытой транзакции."""
        self._states, self._feeds, self._issues, self._schedule = (
            states,
            feeds,
            issues,
            schedule,
        )
        self._clock, self._ids = clock, ids

    @staticmethod
    def rejection(feed: Feed, task: ExportTaskVO) -> str | None:
        """Сверяет текущую схему, настройки и возможность публикации."""
        if feed.status not in (FeedStatus.DRAFT, FeedStatus.ACTIVE):
            return "FEED_INACTIVE"
        if (
            feed.schema != task.snapshot.schema
            or feed.export_settings != task.snapshot.settings
        ):
            return "FEED_CHANGED"
        return None

    async def finish(
        self,
        *,
        tenant_id: UUID,
        feed: Feed,
        state: FeedExportState,
        task: ExportTaskVO,
        counts: ExportCountsVO,
        issues: Iterable[FeedExportIssueDTO] = (),
        file_id: UUID | None = None,
        failed_code: str | None = None,
    ) -> None:
        """Записывает конечный результат и ставит очистку неиспользуемого файла."""
        now = self._clock.now()
        active = None
        retired = file_id
        if failed_code is not None:
            outcome, reason = ExportOutcome.FAILED, failed_code
        else:
            reason = self.rejection(feed, task)
            if reason is None:
                reason = publication_rejection_reason(
                    task.snapshot.settings.validation_policy, counts
                )
            outcome = ExportOutcome.REJECTED if reason else ExportOutcome.PUBLISHED
        if outcome is ExportOutcome.PUBLISHED:
            if file_id is None or task.as_of is None:
                raise RuntimeError("Готовый файл обязателен для публикации.")
            active = ActiveExportVO(
                EntityIdVO(file_id),
                task.snapshot.settings.format_settings.format,
                task.as_of,
                now,
            )
            published = feed.publish_export(
                FeedPublicLinkIdVO(self._ids.new()), now=now
            )
            if published is not feed:
                await self._feeds.save(published, expected_version=feed.version)
            retired = state.active.file_id.uuid if state.active is not None else None
        report = ExportReportVO(
            now,
            task.as_of,
            task.snapshot.settings.validation_policy,
            outcome,
            counts,
            failed_code is None,
            reason,
        )
        await self._states.save(state.finish(task.job_id, report=report, file=active))
        await self._issues.replace(feed.id.uuid, issues)

        if retired is not None:
            # Stream requests that already opened the previous file finish independently.
            await self._schedule(
                ScheduleScheduledJobCommand(
                    tenant_id,
                    RETIRE_FILE_JOB_TYPE,
                    {"file_id": str(retired), "actor_id": str(task.requested_by)},
                    now + timedelta(minutes=5),
                )
            )
