"""Проверки архитектуры постоянного XML-фида по backend.md."""

import ast
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1] / "src/modules/channels"


class ContentFeedArchitectureTests(TestCase):
    def test_layers_concrete_types_docstrings_and_factories(self) -> None:
        """Проверяет фабрики, конкретные типы и направление импортов каждого слоя."""
        for layer in ("domain", "application", "infrastructure", "presentation"):
            for path in (ROOT / layer / "content_feed").rglob("*.py"):
                source = path.read_text()
                if path.name == "__init__.py":
                    self.assertEqual(source, "")
                self.assertNotIn("TypeVar", source)
                self.assertNotIn("Generic[", source)
                for node in ast.walk(ast.parse(source)):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertIsNotNone(node.returns, f"{path}:{node.name}")
                        self.assertTrue(ast.get_docstring(node), f"{path}:{node.name}")
                        for arg in (
                            *node.args.args,
                            *node.args.posonlyargs,
                            *node.args.kwonlyargs,
                        ):
                            if arg.arg not in {"self", "cls"}:
                                self.assertIsNotNone(
                                    arg.annotation, f"{path}:{arg.arg}"
                                )
                        if node.name == "__post_init__":
                            self.assertEqual(path.name, "value_object.py")
                    if isinstance(node, ast.ImportFrom) and layer in {
                        "domain",
                        "application",
                    }:
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
                            f"{path}:{module}",
                        )
                        if layer == "domain":
                            self.assertFalse(
                                module.startswith("src.modules.channels.application"),
                                str(path),
                            )
        aggregate = (ROOT / "domain/content_feed/aggregate.py").read_text()
        self.assertIn("def create(", aggregate)
        self.assertIn("def restore(", aggregate)
        self.assertIn("cls.restore(", aggregate)

    def test_use_cases_and_http_methods_have_separate_contracts(self) -> None:
        """Проверяет самостоятельные файлы и контракты сценариев."""
        commands = (
            "create_content_feed",
            "change_content_feed_source",
            "enable_content_feed",
            "disable_content_feed",
            "rotate_feed_access",
            "revoke_feed_access",
            "delete_content_feed",
        )
        queries = (
            "get_content_feed",
            "list_content_feeds",
            "preview_content_feed",
            "get_content_feed_xml",
        )
        for kind, names in (("command", commands), ("query", queries)):
            for name in names:
                folder = ROOT / "application/content_feed" / kind / name
                for filename in (kind + ".py", "handler.py"):
                    self.assertTrue(
                        (folder / filename).is_file(), str(folder / filename)
                    )
                if name != "delete_content_feed":
                    self.assertTrue((folder / "dto.py").is_file())
                    self.assertTrue(
                        (
                            ROOT
                            / "presentation/content_feed/http/response"
                            / f"{name}.py"
                        ).is_file()
                    )
                self.assertTrue(
                    (
                        ROOT
                        / "presentation/content_feed/http/controller"
                        / f"{name}.py"
                    ).is_file()
                )
        serializer = (
            ROOT / "infrastructure/platforms/prom/feed_serializer.py"
        ).read_text()
        self.assertNotIn("AsyncSession", serializer)
        self.assertNotIn("httpx", serializer)
