"""Архитектурные границы первого среза Feed без I/O и заготовок следующих слоёв."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE = PROJECT_ROOT / "src/modules/feed_builder"
DOMAIN = MODULE / "domain/feed"


class FeedBuilderArchitectureTests(unittest.TestCase):
    """Проверяет направление зависимостей, фабрики, VO и импорт рекурсивных типов."""

    def test_slice_contains_only_domain_and_empty_package_initializers(self) -> None:
        """Не создаёт repositories, evaluator или внешние слои раньше их срезов."""
        self.assertEqual(
            {
                path.name
                for path in MODULE.iterdir()
                if path.is_dir() and path.name != "__pycache__"
            },
            {"domain"},
        )
        self.assertEqual(
            {
                path.name
                for path in (MODULE / "domain").iterdir()
                if path.is_dir() and path.name != "__pycache__"
            },
            {"feed"},
        )
        forbidden = {"repository.py", "evaluator.py", "events.py"}
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

    def test_aggregate_and_entities_only_declare_create_restore(self) -> None:
        """Не добавляет __post_init__, методы изменения, события и исполнение формул."""
        paths = [DOMAIN / "aggregate.py", *sorted((DOMAIN / "entity").glob("*.py"))]
        for path in paths:
            for node in ast.parse(path.read_text()).body:
                if isinstance(node, ast.ClassDef):
                    methods = {
                        item.name
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    }
                    self.assertEqual(methods, {"create", "restore"}, str(path))
                    for method in (
                        item for item in node.body if isinstance(item, ast.FunctionDef)
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
        aliases = ast.parse((DOMAIN / "types.py").read_text())
        self.assertFalse(any(isinstance(node, ast.ClassDef) for node in aliases.body))

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


if __name__ == "__main__":
    unittest.main()
