"""Нормативные ограничения нового Channels: слои, агрегаты и конкретные контракты."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "src/modules/channels"


class ChannelsArchitectureTests(unittest.TestCase):
    """Проверяет архитектуру независимо от функционального результата."""

    def test_layers_annotations_docstrings_and_factories(self) -> None:
        """Все определения аннотированы; Domain не зависит от транспорта и Application."""
        for path in ROOT.rglob("*.py"):
            source = path.read_text()
            if path.name == "__init__.py":
                self.assertEqual(source, "", str(path))
                continue
            tree = ast.parse(source)
            relative = path.relative_to(ROOT)
            layer = relative.parts[0]
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertIsNotNone(node.returns, f"{relative}:{node.name}")
                    args = [
                        *node.args.posonlyargs,
                        *node.args.args,
                        *node.args.kwonlyargs,
                    ]
                    args.extend(
                        (arg for arg in (node.args.vararg, node.args.kwarg) if arg)
                    )
                    for arg in args:
                        if arg.arg not in ("self", "cls"):
                            self.assertIsNotNone(
                                arg.annotation, f"{relative}:{node.name}:{arg.arg}"
                            )
                    self.assertTrue(ast.get_docstring(node), f"{relative}:{node.name}")
                    if node.name == "__post_init__":
                        self.assertIn("value_object", relative.parts)
                if isinstance(node, ast.ClassDef):
                    self.assertTrue(ast.get_docstring(node), str(relative))
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = (
                        [node.module or ""]
                        if isinstance(node, ast.ImportFrom)
                        else [alias.name for alias in node.names]
                    )
                    for name in names:
                        if layer in ("domain", "application"):
                            self.assertFalse(
                                name.startswith(
                                    (
                                        "sqlalchemy",
                                        "fastapi",
                                        "httpx",
                                        "cryptography",
                                        "pydantic",
                                        "src.config",
                                        "src.modules.channels.infrastructure",
                                        "src.modules.channels.presentation",
                                        "src.modules.shared.infrastructure",
                                        "src.modules.shared.presentation",
                                    )
                                ),
                                f"{relative}:{name}",
                            )
                        if layer == "domain":
                            self.assertFalse(
                                name.startswith("src.modules.channels.application"),
                                str(relative),
                            )
                        if name.startswith("src.modules.catalog"):
                            self.assertTrue(
                                relative.parts[:3]
                                == (
                                    "infrastructure",
                                    "product_representation",
                                    "adapter",
                                )
                                or relative
                                in {
                                    Path(
                                        "presentation/product_representation/depends.py"
                                    ),
                                    Path("presentation/publication_import/assembly.py"),
                                    Path("presentation/content_update/assembly.py"),
                                }
                                or relative.parts[:3]
                                in {
                                    ("infrastructure", "publication_import", "adapter"),
                                    ("infrastructure", "content_update", "adapter"),
                                },
                                str(relative),
                            )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if layer == "application" or "persistence" in relative.parts:
                        self.assertNotIn(
                            node.func.attr, ("commit", "rollback"), str(relative)
                        )
            if path.name == "aggregate.py" or relative == Path(
                "domain/channel/entity/connection.py"
            ):
                methods = {
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                }
                self.assertTrue({"create", "restore"} <= methods, str(relative))
            if path.name.endswith("mapper.py"):
                self.assertFalse(
                    any((isinstance(node, ast.Await) for node in ast.walk(tree))),
                    str(relative),
                )

    def test_connection_is_entity_and_queries_do_not_restore_roots(self) -> None:
        """Connection не получает самостоятельный write root или repository."""
        self.assertTrue((ROOT / "domain/channel/entity/connection.py").exists())
        self.assertFalse((ROOT / "domain/connection").exists())
        self.assertFalse((ROOT / "application/connection").exists())
        for path in ROOT.glob("application/*/query/*/handler.py"):
            self.assertNotIn("domain.channel.aggregate", path.read_text())
            self.assertNotIn("domain.external_publication.aggregate", path.read_text())
            self.assertNotIn("domain.sync_run.aggregate", path.read_text())

    def test_every_scenario_has_concrete_contract_and_explicit_http_files(self) -> None:
        """Каждый сценарий имеет свой вход/handler; None не создаёт пустые DTO."""
        no_results = {
            "unbind_publication",
            "pause_connection",
            "resume_connection",
            "archive_channel",
            "apply_connection_verification",
            "complete_publication_initialization",
        }
        for path in ROOT.glob("application/*/*/*/handler.py"):
            if path.parent.parent.name not in ("command", "query"):
                continue
            folder = path.parent
            kind = folder.parent.name
            self.assertTrue((folder / (kind + ".py")).exists(), str(folder))
            self.assertEqual(
                (folder / "dto.py").exists(), folder.name not in no_results, str(folder)
            )
        for path in ROOT.glob("presentation/*/http/controller/*.py"):
            if path.name == "__init__.py":
                continue
            self.assertEqual(
                (path.parent.parent / "response" / path.name).exists(),
                path.stem not in no_results,
                str(path),
            )
            tree = ast.parse(path.read_text())
            imports = [
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            ]
            self.assertTrue(any((".depends" in name for name in imports)), str(path))

    def test_platform_specific_implementations_stay_in_plugins(self) -> None:
        """Общие handlers не содержат ветвлений Prom/WooCommerce."""
        for path in list((ROOT / "domain").rglob("*.py")) + list(
            (ROOT / "application").rglob("*.py")
        ):
            source = path.read_text().lower()
            self.assertNotIn("woocommerce", source, str(path))
            self.assertNotIn("'prom'", source, str(path))
            self.assertNotIn('"prom"', source, str(path))
