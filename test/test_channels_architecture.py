"""Архитектурные границы текущего bounded context Channels."""

import ast
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1] / "src/modules/channels"


class ChannelsArchitectureTests(unittest.TestCase):
    """Защищает границы слоёв без привязки к конкретным именам обработчиков."""

    def test_all_modules_import_in_a_fresh_process(self) -> None:
        """Проверяет реальные импорты независимо от порядка загрузки тестов."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import importlib, pkgutil; import src.modules.channels as channels; "
                "[importlib.import_module(module.name) for module in "
                "pkgutil.walk_packages(channels.__path__, channels.__name__ + '.')];",
            ],
            cwd=ROOT.parents[2],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_layer_imports_follow_dependency_direction(self) -> None:
        """Domain изолирован от Application и адаптеров; Application не знает transport/SQL."""
        for layer in ("domain", "application", "infrastructure"):
            for path in (ROOT / layer).rglob("*.py"):
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    modules = []
                    if isinstance(node, ast.Import):
                        modules = [name.name for name in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        modules = [node.module]
                    for module in modules:
                        with self.subTest(path=path.relative_to(ROOT), module=module):
                            self.assertNotIn(".presentation", module)
                            if layer in {"domain", "application"}:
                                self.assertNotIn(".infrastructure", module)
                                self.assertFalse(
                                    module.startswith(
                                        (
                                            "sqlalchemy",
                                            "fastapi",
                                            "pydantic",
                                            "src.config",
                                        )
                                    )
                                )
                            if layer == "domain":
                                self.assertNotIn(".application", module)

    def test_factories_and_packages_remain_explicit(self) -> None:
        """Пакеты не реэкспортируют код, __post_init__ остаётся только в VO."""
        for path in ROOT.rglob("*.py"):
            with self.subTest(path=path.relative_to(ROOT)):
                if path.name == "__init__.py":
                    self.assertEqual(path.read_text().strip(), "")
                for node in ast.walk(ast.parse(path.read_text())):
                    if (
                        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name == "__post_init__"
                    ):
                        self.assertEqual(path.parent.name, "value_object")

    def test_http_controllers_do_not_serialize_dataclasses_implicitly(self) -> None:
        """Контракт HTTP не зависит от автоматического раскрытия полей внутреннего DTO."""
        for path in (ROOT / "presentation/http/controller").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and node.module == "dataclasses":
                    self.assertNotIn(
                        "asdict", [name.name for name in node.names], str(path)
                    )
