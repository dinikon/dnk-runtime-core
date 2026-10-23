import ast
import unittest
from pathlib import Path


class CatalogArchitectureTests(unittest.TestCase):
    """Проверяет обязательные файлы, слои, аннотации и отсутствие JSON-хранения."""

    def test_architecture_and_scenario_files(self) -> None:
        """Нормативные правила проверяются независимо от функциональных сценариев."""
        root = Path("src/modules/catalog")
        for path in root.rglob("*.py"):
            text = path.read_text()
            tree = ast.parse(text)
            if path.name == "__init__.py":
                self.assertEqual(text, "", str(path))
            if "/infrastructure/persistence/models/" in str(path):
                self.assertNotIn("JSON", text, str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertIsNotNone(node.returns, f"{path}:{node.name}")
                    self.assertIsNotNone(ast.get_docstring(node), f"{path}:{node.name}")
                    for arg in [
                        *node.args.posonlyargs,
                        *node.args.args,
                        *node.args.kwonlyargs,
                    ]:
                        if arg.arg not in {"self", "cls"}:
                            self.assertIsNotNone(
                                arg.annotation, f"{path}:{node.name}:{arg.arg}"
                            )
                    if node.name == "__post_init__":
                        self.assertIn("/value_object/", str(path))
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "/domain/" in str(path):
                        self.assertFalse(
                            any(
                                f".{layer}." in node.module
                                for layer in [
                                    "application",
                                    "infrastructure",
                                    "presentation",
                                ]
                            ),
                            str(path),
                        )
                    if "/application/" in str(path):
                        self.assertFalse(
                            any(
                                f".{layer}." in node.module
                                for layer in ["infrastructure", "presentation"]
                            ),
                            str(path),
                        )
            if "/application/" in str(path) and path.name in {"command.py", "query.py"}:
                self.assertTrue((path.parent / "handler.py").exists())
                handler_tree = ast.parse((path.parent / "handler.py").read_text())
                execute = next(
                    n
                    for n in ast.walk(handler_tree)
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == "execute"
                )
                has_result = not (
                    isinstance(execute.returns, ast.Constant)
                    and execute.returns.value is None
                )
                scenario, aggregate = path.parent.name, path.parents[2].name
                if scenario in {
                    "find_used_image_files",
                }:
                    self.assertTrue((path.parent / "dto.py").exists())
                    continue
                http = root / "presentation" / aggregate / "http"
                self.assertTrue(
                    (http / "controller" / f"{scenario}.py").exists(), str(path)
                )
                self.assertTrue(
                    (root / "presentation" / aggregate / "depends.py").exists()
                )
                if has_result:
                    self.assertTrue((path.parent / "dto.py").exists(), str(path))
                    if scenario != "get_catalog_item_image_content":
                        self.assertTrue(
                            (http / "response" / f"{scenario}.py").exists(), str(path)
                        )
                else:
                    self.assertFalse((path.parent / "dto.py").exists(), str(path))
                    self.assertFalse(
                        (http / "response" / f"{scenario}.py").exists(), str(path)
                    )
                if path.name == "command.py" and not scenario.startswith("delete_"):
                    self.assertTrue(
                        (http / "request" / f"{scenario}.py").exists(), str(path)
                    )
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
            migration_metadata,
        )

        meta = migration_metadata()
        from sqlalchemy import JSON

        for table in meta.tables.values():
            if table.name.startswith("catalog_"):
                for column in table.columns:
                    self.assertNotIsInstance(column.type, JSON)
