import contextlib
import io
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.management.cli import build_parser
from src.management.commands.tenant_migrations import handle
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrationError,
    validate_schema_name,
)
from src.modules.tenancy.presentation.depends.management import TenantMigrationStatus


class TenantMigrationManagementTests(unittest.IsolatedAsyncioTestCase):
    def test_parser_requires_exactly_one_target(self):
        parser = build_parser()
        for argv in (
            ["tenant-migrations", "upgrade"],
            ["tenant-migrations", "current", str(uuid4()), "--all"],
            [
                "tenant-migrations",
                "revision",
                "--tenant-id",
                str(uuid4()),
                "-m",
                "test",
            ],
        ):
            with (
                self.subTest(argv=argv),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                parser.parse_args(argv)
        self.assertTrue(
            parser.parse_args(["tenant-migrations", "upgrade", "--all"]).all_tenants
        )

    async def test_batch_continues_after_failure_and_returns_nonzero(self):
        ids = [uuid4(), uuid4(), uuid4()]
        management = AsyncMock()
        management.list_ids.return_value = ids
        management.run_one.side_effect = [
            TenantMigrationStatus(
                ids[0], "dnk_a", ("0001_warehouses",), "0001_warehouses"
            ),
            TenantMigrationError("missing schema"),
            TenantMigrationStatus(
                ids[2], "dnk_c", ("0001_warehouses",), "0001_warehouses"
            ),
        ]
        args = build_parser().parse_args(["tenant-migrations", "upgrade", "--all"])
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch(
                "src.management.commands.tenant_migrations.build_tenant_migration_management",
                return_value=management,
            ),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            result = await handle(args)
        self.assertEqual(result, 2)
        self.assertEqual(management.run_one.await_count, 3)
        self.assertIn("succeeded=2 failed=1", output.getvalue())
        self.assertIn(str(ids[1]), errors.getvalue())

    def test_system_and_unsafe_schema_names_are_rejected(self):
        for name in (
            "public",
            "pg_catalog",
            "information_schema",
            "tenant",
            'x";drop schema public',
            "x" * 64,
        ):
            with self.subTest(name=name), self.assertRaises(TenantMigrationError):
                validate_schema_name(name)
