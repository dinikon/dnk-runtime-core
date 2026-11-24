from src.modules.feed_builder.domain.feed.value_object.category_field_type import (
    CategoryFieldTypeVO,
)
from datetime import timedelta

from src.modules.feed_builder.application.export_state.command.request_feed_refresh.command import (
    RequestFeedRefreshCommand,
)
from src.modules.feed_builder.application.export_state.command.request_feed_refresh.dto import (
    RequestFeedRefreshResultDTO,
)
from src.modules.feed_builder.application.export_state.job_types import (
    RECONCILE_JOB_TYPE,
    REFRESH_JOB_TYPE,
)
from src.modules.feed_builder.domain.export_state.repository import (
    FeedExportStateRepositoryProtocol,
)
from src.modules.feed_builder.domain.export_state.value_object.export_snapshot import (
    ExportSnapshotVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_task import (
    ExportTaskVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedVersionConflictError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.domain.feed.policy.calculation_semantics import (
    PriceCalculationSemanticPolicy,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
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


class RequestFeedRefreshHandler:
    """Фиксирует снимок и очередь в одной внешней транзакции."""

    def __init__(
        self,
        feeds: FeedRepositoryProtocol,
        states: FeedExportStateRepositoryProtocol,
        schedule: ScheduleScheduledJobUseCase,
        clock: ClockPort,
        identifiers: UUIdGeneratorProtocol,
    ) -> None:
        """Получает репозитории и scheduler общего UoW."""
        self._feeds, self._states, self._schedule = feeds, states, schedule
        self._clock, self._identifiers = clock, identifiers

    async def execute(
        self, command: RequestFeedRefreshCommand
    ) -> RequestFeedRefreshResultDTO:
        """Ставит одну задачу по проверенной сохранённой схеме и настройкам."""
        feed = await self._feeds.get_for_update(FeedIdVO(command.feed_id))
        if feed.version.value != command.expected_version:
            raise FeedVersionConflictError("Feed уже изменён.")
        if feed.status is FeedStatus.ARCHIVED:
            raise FeedArchivedError("Архивный Feed доступен только для просмотра.")
        if feed.status not in (FeedStatus.DRAFT, FeedStatus.ACTIVE):
            raise InvalidFeedValueError("Обновление недоступно для этого статуса Feed.")
        state = await self._states.get_for_update(feed.id)
        if state.task is not None:
            return RequestFeedRefreshResultDTO(
                state.task.status, state.task.requested_at
            )
        xml = isinstance(feed.export_settings.format_settings, XmlExportSettingsVO)
        if not any(
            field.export.enabled
            and (xml or not isinstance(field.type_definition, CategoryFieldTypeVO))
            for field in feed.schema.fields
        ):
            raise InvalidFeedValueError(
                "В схеме требуется хотя бы одно экспортируемое поле."
            )
        for field in feed.schema.fields:
            definition = field.type_definition
            if (
                isinstance(definition, MoneyFieldTypeVO)
                and definition.value_definition.calculation is not None
            ):
                PriceCalculationSemanticPolicy.ensure_valid(
                    definition.value_definition.calculation
                )

        now = self._clock.now()
        job_id = self._identifiers.new()
        task = ExportTaskVO(
            EntityIdVO(job_id),
            EntityIdVO(command.user_id),
            now,
            ExportSnapshotVO(feed.schema, feed.export_settings),
        )
        await self._states.save(state.request(task))
        await self._schedule(
            ScheduleScheduledJobCommand(
                command.tenant_id,
                REFRESH_JOB_TYPE,
                {"feed_id": str(command.feed_id)},
                now,
                job_id,
            )
        )
        await self._schedule(
            ScheduleScheduledJobCommand(
                command.tenant_id,
                RECONCILE_JOB_TYPE,
                {"feed_id": str(command.feed_id), "job_id": str(job_id)},
                now + timedelta(seconds=30),
            )
        )
        return RequestFeedRefreshResultDTO(task.status, task.requested_at)
