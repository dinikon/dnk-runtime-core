"""Architectural checks for the public Currency boundary and explicit HTTP scenarios."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "src/modules/currency"


class CurrencyArchitectureTests(unittest.TestCase):
    def test_controllers_are_individual_and_do_not_access_storage(self):
        for path in (ROOT / "presentation/http").glob("*/controller/*.py"):
            if path.name == "__init__.py":
                continue
            with self.subTest(path=path):
                tree = ast.parse(path.read_text())
                actions = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
                self.assertEqual(len(actions), 1)
                source = path.read_text()
                for forbidden in (
                    "currency_errors",
                    "def wire(",
                    "contextmanager",
                    ".session",
                    ".repository",
                    "SimpleNamespace",
                ):
                    self.assertNotIn(forbidden, source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        self.assertIsNotNone(node.type)
                        self.assertNotIn(
                            ast.unparse(node.type), ("Exception", "IntegrityError")
                        )

    def test_domain_and_application_dependencies_point_inward(self):
        for layer in ("domain", "application"):
            for path in (ROOT / layer).rglob("*.py"):
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        self.assertEqual(node.level, 0, str(path))
                        self.assertFalse(
                            any(
                                x in module
                                for x in (
                                    ".infrastructure",
                                    ".presentation",
                                    "sqlalchemy",
                                    "fastapi",
                                    "pydantic",
                                    "httpx",
                                )
                            ),
                            str(path),
                        )
                        if layer == "domain":
                            self.assertNotIn(".application", module, str(path))

    def test_conversion_is_local_and_dependencies_are_typed(self):
        resolver = (ROOT / "domain/exchange_rate/service.py").read_text()
        self.assertNotIn("httpx", resolver)
        self.assertNotIn("ExchangeRateProvider", resolver)
        for path in (ROOT / "presentation/depends").glob("*.py"):
            self.assertNotIn("SimpleNamespace", path.read_text())
        self.assertNotIn(
            "get_business_date",
            (ROOT / "application/facade/currency_facade.py").read_text(),
        )
        for removed in (
            "domain/models.py",
            "domain/repositories.py",
            "application/commands.py",
            "application/conversion.py",
            "application/provider.py",
            "presentation/http/boundary.py",
        ):
            self.assertFalse((ROOT / removed).exists())
