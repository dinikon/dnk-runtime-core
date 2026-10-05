"""Dependency direction and direct imports of the global catalog module."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src/modules/reference_data"


class ReferenceDataArchitectureTests(unittest.TestCase):
    def test_internal_layers_point_inward_and_packages_do_not_reexport(self):
        forbidden = {
            "domain": (
                "sqlalchemy",
                "fastapi",
                "pydantic",
                "httpx",
                "src.modules.reference_data.application",
                "src.modules.reference_data.infrastructure",
                "src.modules.reference_data.presentation",
            ),
            "application": (
                "sqlalchemy",
                "fastapi",
                "pydantic",
                "httpx",
                "src.modules.reference_data.infrastructure",
                "src.modules.reference_data.presentation",
            ),
            "infrastructure": ("src.modules.reference_data.presentation",),
        }
        for path in MODULE.rglob("*.py"):
            with self.subTest(path=str(path.relative_to(ROOT))):
                if path.name == "__init__.py":
                    self.assertEqual(path.read_text().strip(), "")
                layer = path.relative_to(MODULE).parts[0]
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = (alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        names = (node.module,)
                    else:
                        continue
                    for name in names:
                        self.assertFalse(
                            name.startswith(forbidden.get(layer, ())), f"{path}: {name}"
                        )
                        if name.startswith("src.modules.reference_data"):
                            self.assertTrue(
                                (ROOT / (name.replace(".", "/") + ".py")).is_file(),
                                f"Indirect import {path}: {name}",
                            )
