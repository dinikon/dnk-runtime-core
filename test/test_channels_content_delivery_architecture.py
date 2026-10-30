"""Архитектурные границы исходящей доставки контента."""

import ast
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1] / "src/modules/channels"


class ContentDeliveryArchitectureTests(TestCase):
    """Проверяет самостоятельный корень и конкретные контракты каждого сценария."""

    def test_scenarios_and_http_methods_have_separate_contracts(self) -> None:
        """Один универсальный handler/DTO не заменяет разные пользовательские намерения."""
        for kind, scenarios in (
            (
                "command",
                (
                    "request_content_delivery",
                    "prepare_content_delivery",
                    "authorize_content_delivery",
                    "apply_content_delivery",
                    "apply_content_reconciliation",
                    "request_content_reconciliation",
                ),
            ),
            ("query", ("get_content_deliveries",)),
        ):
            for scenario in scenarios:
                folder = ROOT / "application/content_delivery" / kind / scenario
                for name in (kind + ".py", "handler.py", "dto.py"):
                    self.assertTrue((folder / name).is_file(), str(folder / name))
        for scenario in (
            "request_content_delivery",
            "get_content_deliveries",
            "request_content_reconciliation",
        ):
            for responsibility in ("controller", "response"):
                self.assertTrue(
                    (
                        ROOT
                        / "presentation/content_delivery/http"
                        / responsibility
                        / (scenario + ".py")
                    ).is_file()
                )

    def test_layers_types_factories_and_package_boundaries(self) -> None:
        """Domain/Application не импортируют транспорт, SQL или модели платформ."""
        for layer in ("domain", "application", "infrastructure", "presentation"):
            for path in (ROOT / layer / "content_delivery").rglob("*.py"):
                source = path.read_text()
                if path.name == "__init__.py":
                    self.assertEqual(source, "")
                self.assertNotIn("TypeVar", source)
                self.assertNotIn("Generic[", source)
                for node in ast.walk(ast.parse(source)):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertIsNotNone(node.returns, f"{path}: {node.name}")
                        self.assertTrue(ast.get_docstring(node), f"{path}: {node.name}")
                        if node.name == "__post_init__":
                            self.assertEqual(path.name, "value_object.py")
                        for arg in (
                            *node.args.args,
                            *node.args.posonlyargs,
                            *node.args.kwonlyargs,
                        ):
                            if arg.arg not in {"self", "cls"}:
                                self.assertIsNotNone(
                                    arg.annotation, f"{path}: {arg.arg}"
                                )
                    if isinstance(node, ast.ImportFrom) and layer in {
                        "domain",
                        "application",
                    }:
                        module = node.module or ""
                        self.assertFalse(
                            module.startswith(
                                (
                                    "sqlalchemy",
                                    "pydantic",
                                    "fastapi",
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
        source = (ROOT / "domain/content_delivery/aggregate.py").read_text()
        self.assertIn("def create(", source)
        self.assertIn("def restore(", source)
        self.assertNotIn("__post_init__", source)
