from dataclasses import dataclass
from datetime import datetime

from src.modules.feed_builder.domain.export_state.enum.export_outcome import (
    ExportOutcome,
)
from src.modules.feed_builder.domain.export_state.error import InvalidExportStateError
from src.modules.feed_builder.domain.export_state.policy.publication import (
    publication_rejection_reason,
)
from src.modules.feed_builder.domain.export_state.value_object.export_counts import (
    ExportCountsVO,
)
from src.modules.feed_builder.domain.feed.enum.validation_policy import ValidationPolicy
from src.modules.feed_builder.domain.validation import require_datetime


@dataclass(frozen=True, slots=True)
class ExportReportVO:
    """Сохраняет итог только последней завершённой проверки."""

    completed_at: datetime
    as_of: datetime | None
    validation_policy: ValidationPolicy
    outcome: ExportOutcome
    counts: ExportCountsVO
    is_complete: bool
    reason_code: str | None = None

    def __post_init__(self) -> None:
        """Проверяет отчёт для успеха, отклонения и технического сбоя."""
        require_datetime(self.completed_at, error=InvalidExportStateError)
        if self.as_of is not None:
            require_datetime(self.as_of, error=InvalidExportStateError)
            if self.as_of > self.completed_at:
                raise InvalidExportStateError("Отчёт предшествует расчёту.")
        if (
            not isinstance(self.validation_policy, ValidationPolicy)
            or not isinstance(self.outcome, ExportOutcome)
            or not isinstance(self.counts, ExportCountsVO)
            or type(self.is_complete) is not bool
            or (
                self.is_complete
                and (
                    self.as_of is None
                    or self.counts.processed != self.counts.total_items
                )
            )
        ):
            raise InvalidExportStateError("Несогласованный отчёт экспорта.")
        if self.outcome is ExportOutcome.PUBLISHED:
            if (
                not self.is_complete
                or publication_rejection_reason(self.validation_policy, self.counts)
                is not None
                or self.reason_code is not None
            ):
                raise InvalidExportStateError(
                    "Для публикации нужен полный отчёт с допустимым результатом проверки."
                )
        elif (
            not isinstance(self.reason_code, str)
            or not self.reason_code.strip()
            or len(self.reason_code) > 64
        ):
            raise InvalidExportStateError("Для отказа нужен код результата.")
