"""Направление зависимостей и границы транзакций первого среза Catalog."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "src/modules/catalog"


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    return [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ] + [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]


class CatalogArchitectureTests(unittest.TestCase):
    def test_domain_and_application_depend_only_inward(self) -> None:
        forbidden = (
            "sqlalchemy",
            "fastapi",
            "pydantic",
            "src.modules.catalog.infrastructure",
            "src.modules.catalog.presentation",
            "src.modules.inventory",
            "src.modules.reference_data",
            "src.modules.shared.infrastructure",
            "src.modules.shared.presentation",
        )
        for layer in ("domain", "application"):
            for path in (CATALOG / layer).rglob("*.py"):
                for name in imported_modules(path):
                    self.assertFalse(name.startswith(forbidden), f"{path}: {name}")

    def test_repository_and_handlers_leave_transactions_to_uow(self) -> None:
        for layer in (
            "application",
            "infrastructure/product/persistence",
        ):
            for path in (CATALOG / layer).rglob("*.py"):
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(
                        node.func, ast.Attribute
                    ):
                        self.assertNotIn(
                            node.func.attr, ("commit", "rollback"), str(path)
                        )
                if "repository.py" in path.name:
                    self.assertNotIn("schema_translate_map", path.read_text())

    def test_entrypoints_import_independently(self) -> None:
        for module in (
            "src.modules.catalog.domain.product.aggregate",
            "src.modules.catalog.application.product.command.create_product.handler",
            "src.modules.catalog.application.product.query.get_product.handler",
            "src.modules.catalog.infrastructure.persistence.models.product",
            "src.modules.catalog.infrastructure.product.persistence.repository",
            "src.modules.catalog.presentation.product.router",
            "src.modules.tenant_persistence",
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import importlib,sys; importlib.import_module(sys.argv[1])",
                    module,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
