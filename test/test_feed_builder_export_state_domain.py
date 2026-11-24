"""Проверяет жизненный цикл одного состояния экспорта Feed."""

from datetime import UTC, datetime, timedelta
from unittest import TestCase
from uuid import uuid4

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
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

NOW = datetime(2026, 11, 22, tzinfo=UTC)


class ExportStateDomainTests(TestCase):
    """Проверяет повторы, инварианты результата и сохранение прежнего файла."""

    def task(self, now: datetime) -> ExportTaskVO:
        """Создаёт задачу с фиксированными настройками CSV."""
        return ExportTaskVO(
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            now,
            ExportSnapshotVO(
                FeedSchemaVO(),
                FeedExportSettingsVO(format_settings=CsvExportSettingsVO()),
            ),
        )

    def test_retries_preserve_as_of_and_rejected_report_preserves_file(self) -> None:
        """Заменяет только последний отчёт, когда STRICT отклонил новую проверку."""
        task = self.task(NOW)
        requested = FeedExportState.create(FeedIdVO(uuid4())).request(task)
        self.assertIs(requested.request(self.task(NOW)), requested)
        started = requested.start(task.job_id, NOW)
        self.assertIs(started.start(task.job_id, NOW + timedelta(minutes=1)), started)
        file = ActiveExportVO(EntityIdVO(uuid4()), ExportFormat.CSV, NOW, NOW)
        state = started.finish(
            task.job_id,
            file=file,
            report=ExportReportVO(
                NOW,
                NOW,
                ValidationPolicy.STRICT,
                ExportOutcome.PUBLISHED,
                ExportCountsVO(2, 1, 1),
                True,
            ),
        )
        later = NOW + timedelta(minutes=2)
        replacement = self.task(later)
        waiting = state.request(replacement)
        self.assertEqual(waiting.report, state.report)
        report = ExportReportVO(
            later,
            later,
            ValidationPolicy.STRICT,
            ExportOutcome.REJECTED,
            ExportCountsVO(3, 1, 1, 1),
            True,
            "STRICT_REJECTED",
        )
        running = waiting.start(replacement.job_id, later)
        with self.assertRaises(InvalidExportStateError):
            running.finish(task.job_id, report=report)
        rejected = running.finish(replacement.job_id, report=report)
        self.assertEqual(rejected.report, report)
        self.assertEqual(rejected.active, file)
        self.assertIsNone(rejected.task)

    def test_strict_rejects_incomplete_or_invalid_published_report(self) -> None:
        """Успешный снимок содержит полный и корректный отчёт."""
        for counts, complete in (
            (ExportCountsVO(2, 1), False),
            (ExportCountsVO(2, 1, 0, 1), True),
        ):
            with self.assertRaises(InvalidExportStateError):
                ExportReportVO(
                    NOW,
                    NOW,
                    ValidationPolicy.STRICT,
                    ExportOutcome.PUBLISHED,
                    counts,
                    complete,
                )

    def test_skip_invalid_requires_a_publishable_result(self) -> None:
        """Проверяет успех с предупреждениями и отказ без пригодных позиций."""
        for counts in (ExportCountsVO(3, 1, 1, 1), ExportCountsVO(2, 0, 1, 1)):
            report = ExportReportVO(
                NOW,
                NOW,
                ValidationPolicy.SKIP_INVALID,
                ExportOutcome.PUBLISHED,
                counts,
                True,
            )
            self.assertEqual(report.counts, counts)
        with self.assertRaises(InvalidExportStateError):
            ExportReportVO(
                NOW,
                NOW,
                ValidationPolicy.SKIP_INVALID,
                ExportOutcome.PUBLISHED,
                ExportCountsVO(2, 0, 0, 2),
                True,
            )
