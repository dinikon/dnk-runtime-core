"""Нормативные границы и отдельные сценарии media-среза."""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import HTTPException, Request

from src.modules.channels.presentation.content_media.depends import get_media_tenant
from src.modules.tenancy.domain.tenant_domain.error import TenantHostNotFoundError

ROOT = Path(__file__).resolve().parents[1] / "src/modules/channels"


class MediaArchitectureTests(TestCase):
    """Проверяет конкретные контракты и отсутствие обратных зависимостей."""

    def test_scenarios_have_own_inputs_results_and_handlers(self) -> None:
        """Команды и запросы не подменяются универсальным CRUD или DTO."""
        for kind, scenarios in (
            (
                "command",
                (
                    "prepare_gallery",
                    "revoke_media_access",
                    "renew_media_access",
                    "begin_media_transfer",
                    "record_media_transfer_result",
                    "invalidate_media_reference",
                ),
            ),
            ("query", ("get_media_content", "find_used_image_files")),
        ):
            for scenario in scenarios:
                folder = ROOT / "application/content_media" / kind / scenario
                for name in (kind + ".py", "handler.py", "dto.py"):
                    self.assertTrue((folder / name).is_file(), str(folder / name))

    def test_layers_annotations_docstrings_and_factories(self) -> None:
        """Новый код имеет конкретные типы, create/restore и пустые init-файлы."""
        for layer in ("domain", "application", "infrastructure", "presentation"):
            for path in (ROOT / layer / "content_media").rglob("*.py"):
                source = path.read_text()
                if path.name == "__init__.py":
                    self.assertEqual(source, "")
                for node in ast.walk(ast.parse(source)):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertIsNotNone(node.returns, str(path))
                        self.assertTrue(ast.get_docstring(node), f"{path}: {node.name}")
                        for arg in (
                            node.args.posonlyargs
                            + node.args.args
                            + node.args.kwonlyargs
                        ):
                            if arg.arg not in ("self", "cls"):
                                self.assertIsNotNone(
                                    arg.annotation, f"{path}: {arg.arg}"
                                )
                        self.assertNotEqual(node.name, "__post_init__")
                    if isinstance(node, ast.ImportFrom) and layer in (
                        "domain",
                        "application",
                    ):
                        module = node.module or ""
                        self.assertFalse(
                            module.startswith(
                                (
                                    "sqlalchemy",
                                    "fastapi",
                                    "pydantic",
                                    "src.modules.channels.infrastructure",
                                    "src.modules.channels.presentation",
                                    "src.modules.shared.infrastructure",
                                )
                            ),
                            str(path),
                        )
                        if layer == "domain":
                            self.assertFalse(
                                module.startswith("src.modules.channels.application"),
                                str(path),
                            )
        methods = {
            node.name
            for node in ast.walk(
                ast.parse((ROOT / "domain/content_media/aggregate.py").read_text())
            )
            if isinstance(node, ast.FunctionDef)
        }
        self.assertTrue(
            {"create", "restore", "revoke", "begin_transfer", "record_result"}
            <= methods
        )


class MediaTenantResolutionTests(IsolatedAsyncioTestCase):
    """Проверяет реальную dependency разрешения tenant без cookie или principal."""

    async def test_canonical_tenant_comes_from_host_resolver_and_requires_admission(
        self,
    ) -> None:
        """Клиентский X-Tenant-ID не выбирает схему и не меняет API origin."""
        tenant = uuid4()
        request = Request(
            {
                "type": "http",
                "scheme": "https",
                "path": "/api/channels/content-media/x/image.png",
                "headers": [
                    (b"host", b"tenant.example"),
                    (b"x-tenant-id", str(uuid4()).encode()),
                ],
                "state": {"tenant_connection": object()},
            }
        )
        resolver = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    tenant_id=tenant,
                    api_host="canonical.example",
                    host="tenant.example",
                )
            )
        )
        result = await get_media_tenant(request, resolver)
        self.assertEqual(
            (result.id, result.base_url), (tenant, "https://canonical.example")
        )
        self.assertEqual(resolver.execute.call_args.args[0].host, "tenant.example")
        del request.state.tenant_connection
        with self.assertRaises(HTTPException) as denied:
            await get_media_tenant(request, resolver)
        self.assertEqual(denied.exception.status_code, 404)
        resolver.execute.side_effect = TenantHostNotFoundError("unknown.example")
        with self.assertRaises(HTTPException) as missing:
            await get_media_tenant(request, resolver)
        self.assertEqual(missing.exception.status_code, 404)
