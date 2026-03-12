from __future__ import annotations

import unittest

from src.modules.runtime_schema.infrastructure.ddl_models import (
    DdlDiff,
    DdlOperation,
    DdlOperationKind,
    DdlPlan,
    ExecutionReport,
    MigrationJournalEntry,
    SchemaSnapshot,
)


class TestDdlModels(unittest.TestCase):
    def test_schema_snapshot_empty(self) -> None:
        snapshot = SchemaSnapshot.empty()
        self.assertEqual(snapshot.tables, {})

    def test_diff_and_plan_is_empty(self) -> None:
        diff = DdlDiff()
        self.assertTrue(diff.is_empty())

        operation = DdlOperation(
            key="op_1",
            kind=DdlOperationKind.CREATE_TABLE,
            sql="SELECT 1",
        )
        plan = DdlPlan(operations=(operation,))
        self.assertFalse(plan.is_empty())

    def test_migration_journal_entry_factories(self) -> None:
        applied = MigrationJournalEntry.applied(
            operation_key="op_1",
            operation_sql="SELECT 1",
        )
        self.assertEqual(applied.status, "APPLIED")
        self.assertIsNotNone(applied.applied_at)

        failed = MigrationJournalEntry.failed(
            operation_key="op_2",
            operation_sql="BROKEN",
            error_message="boom",
        )
        self.assertEqual(failed.status, "FAILED")
        self.assertIsNone(failed.applied_at)

    def test_execution_report_applied_operations(self) -> None:
        operation = DdlOperation(
            key="op_1",
            kind=DdlOperationKind.CREATE_INDEX,
            sql="SQL",
        )
        report = ExecutionReport(
            operations=(operation,),
            journal_entries=(MigrationJournalEntry.applied(operation_key="op_1", operation_sql="SQL"),),
        )
        self.assertEqual(report.applied_operations, 1)


if __name__ == "__main__":
    unittest.main()

