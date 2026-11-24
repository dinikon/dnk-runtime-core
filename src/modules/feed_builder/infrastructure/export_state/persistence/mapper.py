from collections.abc import Mapping

from src.modules.feed_builder.application.feed.schema_document import schema_document
from src.modules.feed_builder.domain.export_state.aggregate import FeedExportState
from src.modules.feed_builder.domain.export_state.enum.export_outcome import (
    ExportOutcome,
)
from src.modules.feed_builder.domain.export_state.error import InvalidExportStateError
from src.modules.feed_builder.domain.export_state.value_object.active_export import (
    ActiveExportVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_counts import (
    ExportCountsVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_report import (
    ExportReportVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_snapshot import (
    ExportSnapshotVO,
)
from src.modules.feed_builder.domain.export_state.value_object.export_task import (
    ExportTaskVO,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.feed.enum.validation_policy import ValidationPolicy
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.infrastructure.feed.persistence.definition_mapper import (
    decode_schema,
)
from src.modules.feed_builder.infrastructure.feed.persistence.settings_mapper import (
    settings_document,
    settings_from_document,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FeedExportStateMapper:
    """Восстанавливает типизированные части агрегата из одной SQL-строки."""

    @staticmethod
    def to_domain(row: Mapping) -> FeedExportState:
        """Преобразует нормализованные колонки и временный снимок."""
        task = report = active = None
        if row["job_id"] is not None:
            snapshot = row["definition_snapshot"]
            task = ExportTaskVO(
                EntityIdVO(row["job_id"]),
                EntityIdVO(row["requested_by"]),
                row["requested_at"],
                ExportSnapshotVO(
                    decode_schema(snapshot["schema"]),
                    settings_from_document(snapshot["settings"]),
                    snapshot["engine_version"],
                ),
                row["started_at"],
                row["job_as_of"],
            )
            if task.status != row["job_status"]:
                raise InvalidExportStateError("Некорректный сохранённый статус задачи.")
        if row["last_completed_at"] is not None:
            report = ExportReportVO(
                row["last_completed_at"],
                row["last_as_of"],
                ValidationPolicy(row["last_validation_policy"]),
                ExportOutcome(row["last_outcome"]),
                ExportCountsVO(
                    row["total_items"],
                    row["valid_items"],
                    row["warning_items"],
                    row["rejected_items"],
                ),
                row["last_is_complete"],
                row["last_reason_code"],
            )
        if row["active_file_id"] is not None:
            active = ActiveExportVO(
                EntityIdVO(row["active_file_id"]),
                ExportFormat(row["active_format"]),
                row["active_as_of"],
                row["active_published_at"],
            )
        return FeedExportState.restore(
            feed_id=FeedIdVO(row["feed_id"]), task=task, report=report, active=active
        )

    @staticmethod
    def to_values(state: FeedExportState) -> dict[str, object]:
        """Подготавливает одну запись и очищает данные завершённой задачи."""
        task, report, active = state.task, state.report, state.active
        return {
            "feed_id": state.feed_id.uuid,
            "job_id": task.job_id.uuid if task else None,
            "job_status": task.status.value if task else None,
            "requested_by": task.requested_by.uuid if task else None,
            "requested_at": task.requested_at if task else None,
            "started_at": task.started_at if task else None,
            "job_as_of": task.as_of if task else None,
            "definition_snapshot": (
                {
                    "schema": schema_document(task.snapshot.schema),
                    "settings": settings_document(task.snapshot.settings),
                    "engine_version": task.snapshot.engine_version,
                }
                if task
                else None
            ),
            "last_completed_at": report.completed_at if report else None,
            "last_as_of": report.as_of if report else None,
            "last_validation_policy": (
                report.validation_policy.value if report else None
            ),
            "last_outcome": report.outcome.value if report else None,
            "last_reason_code": report.reason_code if report else None,
            "last_is_complete": report.is_complete if report else None,
            "total_items": report.counts.total_items if report else None,
            "valid_items": report.counts.valid_items if report else None,
            "warning_items": report.counts.warning_items if report else None,
            "rejected_items": report.counts.rejected_items if report else None,
            "active_file_id": active.file_id.uuid if active else None,
            "active_format": active.format.value if active else None,
            "active_as_of": active.as_of if active else None,
            "active_published_at": active.published_at if active else None,
        }
