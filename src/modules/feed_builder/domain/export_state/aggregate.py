from dataclasses import dataclass, replace
from datetime import datetime
from typing import Self

from src.modules.feed_builder.domain.export_state.enum.export_outcome import (
    ExportOutcome,
)
from src.modules.feed_builder.domain.export_state.error import InvalidExportStateError
from src.modules.feed_builder.domain.export_state.value_object.active_export import (
    ActiveExportVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_report import (
    ExportReportVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_task import (
    ExportTaskVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class FeedExportState:
    """Владеет последним отчётом и активным файлом одного фида."""

    feed_id: FeedIdVO
    task: ExportTaskVO | None = None
    report: ExportReportVO | None = None
    active: ActiveExportVO | None = None

    @classmethod
    def create(cls, feed_id: FeedIdVO) -> Self:
        """Создаёт пустое состояние выдачи."""
        return cls.restore(feed_id=feed_id)

    @classmethod
    def restore(
        cls,
        *,
        feed_id: FeedIdVO,
        task: ExportTaskVO | None = None,
        report: ExportReportVO | None = None,
        active: ActiveExportVO | None = None,
    ) -> Self:
        """Восстанавливает сохранённое состояние и проверяет его части."""
        if (
            not isinstance(feed_id, FeedIdVO)
            or (task is not None and not isinstance(task, ExportTaskVO))
            or (report is not None and not isinstance(report, ExportReportVO))
            or (active is not None and not isinstance(active, ActiveExportVO))
            or (
                active is not None
                and (report is None or active.published_at > report.completed_at)
            )
            or (
                report is not None
                and report.outcome is ExportOutcome.PUBLISHED
                and (
                    active is None
                    or active.as_of != report.as_of
                    or active.published_at != report.completed_at
                )
            )
            or (
                task is not None
                and report is not None
                and task.requested_at < report.completed_at
            )
        ):
            raise InvalidExportStateError("Несогласованное состояние экспорта.")
        return cls(feed_id, task, report, active)

    def request(self, task: ExportTaskVO) -> Self:
        """Ставит следующую задачу или сохраняет уже ожидающую пересборку."""
        if self.task is not None:
            return self
        if task.started_at is not None:
            raise InvalidExportStateError("Новая задача ещё не запущена.")
        return self.restore(
            feed_id=self.feed_id, task=task, report=self.report, active=self.active
        )

    def start(self, job_id: EntityIdVO, now: datetime) -> Self:
        """Фиксирует начало и расчётное время один раз."""
        task = self._require_task(job_id)
        if task.started_at is not None:
            return self
        return replace(self, task=replace(task, started_at=now, as_of=now))

    def finish(
        self,
        job_id: EntityIdVO,
        *,
        report: ExportReportVO,
        file: ActiveExportVO | None = None,
    ) -> Self:
        """Заменяет отчёт и при публикации переключает активный файл."""
        task = self._require_task(job_id)
        if (
            report.as_of != task.as_of
            or report.completed_at < task.requested_at
            or report.validation_policy != task.snapshot.settings.validation_policy
            or (report.outcome is ExportOutcome.PUBLISHED) != (file is not None)
            or (
                file is not None
                and file.format != task.snapshot.settings.format_settings.format
            )
        ):
            raise InvalidExportStateError("Результат не соответствует задаче экспорта.")
        return self.restore(
            feed_id=self.feed_id, report=report, active=file or self.active
        )

    def _require_task(self, job_id: EntityIdVO) -> ExportTaskVO:
        """Отклоняет запись результата устаревшей задачи."""
        if self.task is None or self.task.job_id != job_id:
            raise InvalidExportStateError("Задача экспорта уже изменилась.")
        return self.task
