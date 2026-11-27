"""Архитектурные границы Feed CRUD и объектных агрегатов следующих срезов."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE = PROJECT_ROOT / "src/modules/feed_builder"
DOMAIN = MODULE / "domain"


class FeedBuilderArchitectureTests(unittest.TestCase):
    """Проверяет направление зависимостей, фабрики, VO и импорт рекурсивных типов."""

    def test_slice_contains_crud_layers_and_empty_package_initializers(self) -> None:
        """Разрешает Feed CRUD без внешних слоёв остальных агрегатов и evaluator."""
        self.assertEqual(
            {
                path.name
                for path in MODULE.iterdir()
                if path.is_dir() and path.name != "__pycache__"
            },
            {"domain", "application", "infrastructure", "presentation"},
        )
        self.assertEqual(
            {
                path.name
                for path in (MODULE / "domain").iterdir()
                if path.is_dir() and path.name != "__pycache__"
            },
            {"feed", "publication", "export_state", "access_key"},
        )
        forbidden = {"events.py"}
        for path in MODULE.rglob("*.py"):
            with self.subTest(path=path):
                self.assertNotIn(path.name, forbidden)
                if path.name == "__init__.py":
                    self.assertEqual(path.read_text(), "")

    def test_domain_dependencies_point_inward_without_io_or_evaluation(self) -> None:
        """Допускает только stdlib и собственный/shared Domain без исполнения выражений."""
        forbidden = (
            "sqlalchemy",
            "fastapi",
            "pydantic",
            "httpx",
            "requests",
            "logging",
            "os",
            "subprocess",
            "socket",
            "pathlib",
            "src.modules.shared.domain.value_object.money",
            "src.modules.currency",
        )
        for path in DOMAIN.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = []
                if isinstance(node, ast.Import):
                    names = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    with self.subTest(path=path, module=name):
                        self.assertFalse(name.startswith(forbidden))
                        if name.startswith("src."):
                            self.assertTrue(
                                name.startswith(
                                    (
                                        "src.modules.feed_builder.domain.",
                                        "src.modules.shared.domain.",
                                    )
                                )
                            )
                            self.assertTrue(
                                (
                                    PROJECT_ROOT / (name.replace(".", "/") + ".py")
                                ).is_file(),
                                f"Нужен прямой импорт: {name}",
                            )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(
                        node.func.id,
                        ("eval", "exec", "open", "compile", "getattr", "__import__"),
                        str(path),
                    )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(
                        node.func.attr,
                        ("now", "utcnow", "uuid4", "uuid7", "commit", "rollback"),
                        str(path),
                    )

    def test_behavior_is_limited_to_implemented_slices(self) -> None:
        """Разрешает только реализованное поведение агрегатов Feed Builder."""
        paths = [
            *sorted(DOMAIN.glob("*/aggregate.py")),
            *sorted(DOMAIN.glob("*/entity/*.py")),
        ]
        for path in paths:
            for node in ast.parse(path.read_text()).body:
                if isinstance(node, ast.ClassDef):
                    methods = {
                        item.name
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    }
                    expected = {"create", "restore"}
                    if path == DOMAIN / "feed/aggregate.py":
                        expected |= {
                            "change_settings",
                            "change_schema",
                            "change_access_mode",
                            "archive",
                            "publish_export",
                            "rotate_public_link",
                            "_set_public_link",
                        }
                    if path == DOMAIN / "export_state/aggregate.py":
                        expected |= {"request", "start", "finish", "_require_task"}
                    if path == DOMAIN / "access_key/aggregate.py":
                        expected.add("revoke")
                    if path == DOMAIN / "publication/aggregate.py":
                        expected |= {
                            "_transition",
                            "enable",
                            "pause",
                            "archive",
                            "restore_participation",
                            "set_override",
                            "reset_override",
                            "_change_overrides",
                        }
                    self.assertEqual(methods, expected, str(path))
                    for method in (
                        item
                        for item in node.body
                        if isinstance(item, ast.FunctionDef)
                        and item.name in {"create", "restore"}
                    ):
                        self.assertTrue(
                            any(
                                isinstance(decorator, ast.Name)
                                and decorator.id == "classmethod"
                                for decorator in method.decorator_list
                            ),
                            str(path),
                        )

    def test_value_objects_are_separate_frozen_types_and_post_init_stays_there(
        self,
    ) -> None:
        """Каждый VO имеет собственный файл, а __post_init__ не попадает в Entity."""
        for path in DOMAIN.rglob("*.py"):
            tree = ast.parse(path.read_text())
            classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
            if path.parent.name == "value_object" and path.name != "__init__.py":
                self.assertEqual(len(classes), 1, str(path))
                self.assertTrue(classes[0].name.endswith("VO"), str(path))
                if classes[0].decorator_list:
                    dataclass = classes[0].decorator_list[0]
                    self.assertIsInstance(dataclass, ast.Call, str(path))
                    self.assertIn(
                        "frozen", {item.arg for item in dataclass.keywords}, str(path)
                    )
                    self.assertTrue(
                        next(
                            item.value.value
                            for item in dataclass.keywords
                            if item.arg == "frozen"
                        )
                    )
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "__post_init__":
                    self.assertEqual(path.parent.name, "value_object", str(path))
        for path in DOMAIN.rglob("types.py"):
            aliases = ast.parse(path.read_text())
            self.assertFalse(
                any(isinstance(node, ast.ClassDef) for node in aliases.body)
            )

    def test_aggregate_links_use_ids_without_schema_revisions(self) -> None:
        """Не связывает агрегаты объектными ссылками и не вводит ревизии схем."""
        for path in DOMAIN.rglob("*.py"):
            self.assertNotIn("revision", path.name, str(path))
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if path.name != "repository.py" and path.parent.name != "policy":
                        self.assertFalse(node.module.endswith(".aggregate"), str(path))
                if isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    self.assertNotIn(
                        node.target.id,
                        {"schema_version", "schema_revision_id", "activation_id"},
                        str(path),
                    )

    def test_amount_model_has_no_fx_or_currency_arithmetic(self) -> None:
        """Не возвращает удалённые денежные литералы, курсы и валюту вычислений."""
        for path in DOMAIN.rglob("*.py"):
            self.assertNotIn(
                path.name,
                {
                    "money_literal.py",
                    "fx_rate.py",
                    "fx_rate_snapshot.py",
                    "fx_rate_snapshot_id.py",
                },
            )
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    self.assertNotIn(
                        node.target.id, {"calculation_currency", "fx_rate_snapshot"}
                    )

    def test_methods_and_functions_have_annotations_and_docstrings(self) -> None:
        """Контракты явно описывают входы/результаты и назначение без универсального Any."""
        for path in DOMAIN.rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.assertIsNotNone(ast.get_docstring(node), str(path))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertIsNotNone(node.returns, f"{path}:{node.name}")
                    self.assertIsNotNone(ast.get_docstring(node), f"{path}:{node.name}")
                    for arg in [
                        *node.args.posonlyargs,
                        *node.args.args,
                        *node.args.kwonlyargs,
                    ]:
                        if arg.arg not in ("self", "cls"):
                            self.assertIsNotNone(
                                arg.annotation, f"{path}:{node.name}:{arg.arg}"
                            )
                if isinstance(node, ast.Name):
                    self.assertNotEqual(node.id, "Any", str(path))

    def test_recursive_modules_import_in_independent_orders(self) -> None:
        """Отдельные точки входа не зависят от предварительного импорта aggregate/types."""
        for path in DOMAIN.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            name = ".".join(path.relative_to(PROJECT_ROOT).with_suffix("").parts)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import importlib, sys; importlib.import_module(sys.argv[1])",
                    name,
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")

    def test_crud_layer_dependencies_and_no_transaction_control(self) -> None:
        """Защищает зависимости слоёв, DTO и общую транзакцию внешнего UoW."""
        for layer in ("application", "infrastructure", "presentation"):
            for path in (MODULE / layer).rglob("*.py"):
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        name = node.module
                        if layer == "application":
                            self.assertFalse(
                                name.startswith(
                                    (
                                        "sqlalchemy",
                                        "fastapi",
                                        "pydantic",
                                        "src.modules.feed_builder.infrastructure",
                                        "src.modules.feed_builder.presentation",
                                    )
                                ),
                                str(path),
                            )
                        if name.startswith("src."):
                            self.assertTrue(
                                (
                                    PROJECT_ROOT / (name.replace(".", "/") + ".py")
                                ).is_file(),
                                str(path),
                            )
                    if isinstance(node, ast.Call) and isinstance(
                        node.func, ast.Attribute
                    ):
                        self.assertNotIn(
                            node.func.attr, {"commit", "rollback"}, str(path)
                        )
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertIsNotNone(node.returns, f"{path}:{node.name}")
                        self.assertIsNotNone(
                            ast.get_docstring(node), f"{path}:{node.name}"
                        )
                        self.assertNotEqual(node.name, "__post_init__", str(path))
                        for arg in [
                            *node.args.posonlyargs,
                            *node.args.args,
                            *node.args.kwonlyargs,
                        ]:
                            if arg.arg not in {"self", "cls"}:
                                self.assertIsNotNone(
                                    arg.annotation, f"{path}:{node.name}:{arg.arg}"
                                )
                    if isinstance(node, ast.Name):
                        self.assertNotEqual(node.id, "Any", str(path))
        for layer in ("application", "presentation"):
            self.assertFalse((MODULE / layer / "generation").exists())


if __name__ == "__main__":
    unittest.main()
