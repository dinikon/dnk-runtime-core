from __future__ import annotations

import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
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
        self.assertEqual(args.seed_path, dnk_config.DEFAULT_SEED_MODULE)
        self.assertIs(args.handler, schema_registry_command.handle_diff)

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
