from dataclasses import dataclass
from datetime import datetime

from src.modules.feed_builder.domain.export_state.enum.export_task_status import (
    ExportTaskStatus,
)
from src.modules.feed_builder.domain.export_state.error import InvalidExportStateError
from src.modules.feed_builder.domain.export_state.value_object.export_snapshot import (
    ExportSnapshotVO,
)
from src.modules.feed_builder.domain.validation import require_datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ExportTaskVO:
    """Хранит идентичность задачи и время, общее для её попыток."""

    job_id: EntityIdVO
    requested_by: EntityIdVO
    requested_at: datetime
    snapshot: ExportSnapshotVO
    started_at: datetime | None = None
    as_of: datetime | None = None

    def __post_init__(self) -> None:
        """Проверяет согласованность времени и снимка задачи."""
        if not (
            isinstance(self.job_id, EntityIdVO)
            and isinstance(self.requested_by, EntityIdVO)
            and isinstance(self.snapshot, ExportSnapshotVO)
        ):
            raise InvalidExportStateError("Некорректная задача экспорта.")
        require_datetime(self.requested_at, error=InvalidExportStateError)
        if (self.started_at is None) != (self.as_of is None):
            raise InvalidExportStateError("Расчётное время фиксируется при старте.")
        if self.started_at is not None and self.as_of is not None:
            require_datetime(self.started_at, error=InvalidExportStateError)
            require_datetime(self.as_of, error=InvalidExportStateError)
            if not self.requested_at <= self.started_at <= self.as_of:
                raise InvalidExportStateError("Некорректное время задачи экспорта.")

    @property
    def status(self) -> ExportTaskStatus:
        """Определяет статус по времени первой попытки."""
        return (
            ExportTaskStatus.RUNNING
            if self.started_at is not None
            else ExportTaskStatus.PENDING
        )
