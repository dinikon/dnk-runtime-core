from __future__ import annotations

import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from uuid import uuid4
from unittest.mock import patch

from src.config import dnk_config
from src.management.cli import build_parser
from src.management.commands import schema_registry as schema_registry_command
from src.modules.schema_registry.application.dto import DiffSchemaResultDTO
from src.modules.schema_registry.domain.error import SchemaRegistryError
from src.modules.shared import EntityIdVO


class SchemaRegistryManagementCommandTests(unittest.IsolatedAsyncioTestCase):
    def test_parser_registers_schema_registry_diff_command(self) -> None:
        tenant_id = uuid4()

        args = build_parser().parse_args(["schema-registry", "diff", str(tenant_id)])

        self.assertEqual(args.tenant_id, tenant_id)
        self.assertFalse(args.all_tenants)
        self.assertEqual(args.seed_path, dnk_config.DEFAULT_SEED_MODULE)
        self.assertIs(args.handler, schema_registry_command.handle_diff)

    def test_parser_registers_schema_registry_diff_all_command(self) -> None:
        args = build_parser().parse_args(["schema-registry", "diff", "--all"])

        self.assertIsNone(args.tenant_id)
        self.assertTrue(args.all_tenants)
        self.assertEqual(args.seed_path, dnk_config.DEFAULT_SEED_MODULE)
        self.assertIs(args.handler, schema_registry_command.handle_diff)

    async def test_handle_diff_requires_tenant_id_or_all(self) -> None:
        stderr = io.StringIO()
        args = argparse.Namespace(
            tenant_id=None,
            all_tenants=False,
            seed_path=dnk_config.DEFAULT_SEED_MODULE,
        )

        with redirect_stderr(stderr):
            exit_code = await schema_registry_command.handle_diff(args)

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue().strip(), "Provide tenant_id or --all.")

    async def test_handle_diff_rejects_tenant_id_and_all_together(self) -> None:
        stderr = io.StringIO()
        args = argparse.Namespace(
            tenant_id=uuid4(),
            all_tenants=True,
            seed_path=dnk_config.DEFAULT_SEED_MODULE,
        )

        with redirect_stderr(stderr):
            exit_code = await schema_registry_command.handle_diff(args)

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            stderr.getvalue().strip(),
            "Provide either tenant_id or --all, not both.",
        )

    async def test_handle_diff_uses_default_seed_path_and_prints_summary(self) -> None:
        tenant_id = uuid4()
        recorded_command = None
        stdout = io.StringIO()

        class UseCaseStub:
            async def execute(self, command):
                nonlocal recorded_command
                recorded_command = command
                return DiffSchemaResultDTO(
                    tenant_id=command.tenant_id.uuid,
                    schema_name="dnk_example",
                    seed_path=command.seed_path,
                    total_operations=4,
                    destructive_operations=1,
                    non_destructive_operations=3,
                    has_changes=True,
                    has_destructive_changes=True,
                )

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        args = argparse.Namespace(
            tenant_id=tenant_id,
            seed_path=dnk_config.DEFAULT_SEED_MODULE,
        )

        with (
            patch.object(
                schema_registry_command,
                "build_diff_schema_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(schema_registry_command, "UnitOfWork", UnitOfWorkStub),
            redirect_stdout(stdout),
        ):
            exit_code = await schema_registry_command.handle_diff(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(recorded_command.tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(recorded_command.seed_path, dnk_config.DEFAULT_SEED_MODULE)
        self.assertIn("OK tenant_id=", stdout.getvalue())
        self.assertIn("operations=4", stdout.getvalue())
        self.assertIn("destructive=1", stdout.getvalue())

    async def test_handle_diff_all_runs_diff_for_all_tenants(self) -> None:
        tenant_ids = [uuid4(), uuid4()]
        recorded_commands = []
        stdout = io.StringIO()
        uow_instances = []

        class SavepointStub:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        class SessionStub:
            def begin_nested(self):
                return SavepointStub()

        class TenantRepositoryStub:
            def __init__(self, _session):
                pass

            async def list_ids(self):
                return [EntityIdVO.from_value(tenant_id) for tenant_id in tenant_ids]

        class UseCaseStub:
            async def execute(self, command):
                recorded_commands.append(command)
                return DiffSchemaResultDTO(
                    tenant_id=command.tenant_id.uuid,
                    schema_name=f"dnk_{command.tenant_id.uuid.hex[:8]}",
                    seed_path=command.seed_path,
                    total_operations=2,
                    destructive_operations=1,
                    non_destructive_operations=1,
                    has_changes=True,
                    has_destructive_changes=True,
                )

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = SessionStub()
                self.exc_type = None
                uow_instances.append(self)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                self.exc_type = exc_type
                return None

        args = argparse.Namespace(
            tenant_id=None,
            all_tenants=True,
            seed_path=dnk_config.DEFAULT_SEED_MODULE,
        )

        with (
            patch.object(
                schema_registry_command,
                "SqlAlchemyTenantRepository",
                TenantRepositoryStub,
            ),
            patch.object(
                schema_registry_command,
                "build_diff_schema_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(schema_registry_command, "UnitOfWork", UnitOfWorkStub),
            redirect_stdout(stdout),
        ):
            exit_code = await schema_registry_command.handle_diff(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [command.tenant_id.uuid for command in recorded_commands],
            tenant_ids,
        )
        self.assertIsNone(uow_instances[0].exc_type)
        self.assertIn("SUMMARY tenants=2 succeeded=2 failed=0", stdout.getvalue())
        self.assertIn("operations=4", stdout.getvalue())
        self.assertIn("rolled_back=false", stdout.getvalue())

    async def test_handle_diff_all_continues_after_schema_registry_error_and_rolls_back(
        self,
    ) -> None:
        tenant_ids = [uuid4(), uuid4(), uuid4()]
        failed_tenant_id = tenant_ids[1]
        recorded_commands = []
        stdout = io.StringIO()
        stderr = io.StringIO()
        uow_instances = []

        class SavepointStub:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        class SessionStub:
            def begin_nested(self):
                return SavepointStub()

        class TenantRepositoryStub:
            def __init__(self, _session):
                pass

            async def list_ids(self):
                return [EntityIdVO.from_value(tenant_id) for tenant_id in tenant_ids]

        class UseCaseStub:
            async def execute(self, command):
                recorded_commands.append(command)
                if command.tenant_id.uuid == failed_tenant_id:
                    raise SchemaRegistryError("boom")
                return DiffSchemaResultDTO(
                    tenant_id=command.tenant_id.uuid,
                    schema_name=f"dnk_{command.tenant_id.uuid.hex[:8]}",
                    seed_path=command.seed_path,
                    total_operations=3,
                    destructive_operations=1,
                    non_destructive_operations=2,
                    has_changes=True,
                    has_destructive_changes=True,
                )

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = SessionStub()
                self.exc_type = None
                uow_instances.append(self)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                self.exc_type = exc_type
                return None

        args = argparse.Namespace(
            tenant_id=None,
            all_tenants=True,
            seed_path=dnk_config.DEFAULT_SEED_MODULE,
        )

        with (
            patch.object(
                schema_registry_command,
                "SqlAlchemyTenantRepository",
                TenantRepositoryStub,
            ),
            patch.object(
                schema_registry_command,
                "build_diff_schema_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(schema_registry_command, "UnitOfWork", UnitOfWorkStub),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = await schema_registry_command.handle_diff(args)

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            [command.tenant_id.uuid for command in recorded_commands],
            tenant_ids,
        )
        self.assertIs(
            uow_instances[0].exc_type,
            schema_registry_command._DiffAllRollback,
        )
        self.assertIn(
            f"ERROR tenant_id={failed_tenant_id} error=boom",
            stderr.getvalue(),
        )
        self.assertIn("SUMMARY tenants=3 succeeded=2 failed=1", stdout.getvalue())
        self.assertIn("operations=6", stdout.getvalue())
        self.assertIn("rolled_back=true", stdout.getvalue())

    async def test_handle_diff_returns_2_for_schema_registry_error(self) -> None:
        tenant_id = uuid4()
        stderr = io.StringIO()
        recorded_exc_type = None

        class UseCaseStub:
            async def execute(self, _command):
                raise SchemaRegistryError("boom")

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                nonlocal recorded_exc_type
                recorded_exc_type = exc_type
                return None

        args = argparse.Namespace(
            tenant_id=tenant_id,
            seed_path=dnk_config.DEFAULT_SEED_MODULE,
        )

        with (
            patch.object(
                schema_registry_command,
                "build_diff_schema_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(schema_registry_command, "UnitOfWork", UnitOfWorkStub),
            redirect_stderr(stderr),
        ):
            exit_code = await schema_registry_command.handle_diff(args)

        self.assertEqual(exit_code, 2)
        self.assertEqual(stderr.getvalue().strip(), "boom")
        self.assertIs(recorded_exc_type, SchemaRegistryError)

    async def test_handle_diff_all_does_not_swallow_unexpected_error(self) -> None:
        tenant_id = uuid4()

        class SavepointStub:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        class SessionStub:
            def begin_nested(self):
                return SavepointStub()

        class TenantRepositoryStub:
            def __init__(self, _session):
                pass

            async def list_ids(self):
                return [EntityIdVO.from_value(tenant_id)]

        class UseCaseStub:
            async def execute(self, _command):
                raise RuntimeError("unexpected")

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = SessionStub()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        args = argparse.Namespace(
            tenant_id=None,
            all_tenants=True,
            seed_path=dnk_config.DEFAULT_SEED_MODULE,
        )

        with (
            patch.object(
                schema_registry_command,
                "SqlAlchemyTenantRepository",
                TenantRepositoryStub,
            ),
            patch.object(
                schema_registry_command,
                "build_diff_schema_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(schema_registry_command, "UnitOfWork", UnitOfWorkStub),
        ):
            with self.assertRaises(RuntimeError):
                await schema_registry_command.handle_diff(args)

    async def test_handle_diff_does_not_swallow_unexpected_error(self) -> None:
        tenant_id = uuid4()

        class UseCaseStub:
            async def execute(self, _command):
                raise RuntimeError("unexpected")

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        args = argparse.Namespace(
            tenant_id=tenant_id,
            seed_path=dnk_config.DEFAULT_SEED_MODULE,
        )

        with (
            patch.object(
                schema_registry_command,
                "build_diff_schema_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(schema_registry_command, "UnitOfWork", UnitOfWorkStub),
        ):
            with self.assertRaises(RuntimeError):
                await schema_registry_command.handle_diff(args)
