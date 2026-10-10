"""Исполняемый перечень нормативных требований файлового модуля."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "src/modules/files"
SCENARIOS = {
    "storage_provider/command/register_system_storage": "RegisterSystemStorageResultDTO",
    "bucket/command/provision_system_bucket": "ProvisionSystemBucketResultDTO",
    "stored_file/command/upload_file": "UploadFileResultDTO",
    "stored_file/query/get_file_content": "GetFileContentResultDTO",
    "storage_provider/query/list_providers": "tuple[ProviderListItemDTO, ...]",
    "bucket/query/list_buckets": "tuple[BucketListItemDTO, ...]",
    "stored_file/command/cleanup_orphaned_objects": "CleanupOrphanedObjectsResultDTO",
    "bucket/command/purge_tenant_storage": "None",
}


class FilesArchitectureTests(unittest.TestCase):
    """Проверяет границы слоёв независимо от функциональных тестов."""

    def test_scenarios_are_complete_and_have_specific_results(self) -> None:
        """Каждый сценарий имеет отдельный вход, handler и свой результат."""
        for scenario, result in SCENARIOS.items():
            folder = ROOT / "application" / scenario
            category = scenario.split("/")[1]
            self.assertTrue((folder / f"{category}.py").is_file(), scenario)
            tree = ast.parse((folder / "handler.py").read_text())
            execute = next(
                n
                for n in ast.walk(tree)
                if isinstance(n, ast.AsyncFunctionDef) and n.name == "execute"
            )
            self.assertEqual(ast.unparse(execute.returns), result)
            self.assertEqual((folder / "dto.py").is_file(), result != "None")

    def test_imports_annotations_docstrings_factories_and_transaction_boundaries(
        self,
    ) -> None:
        """Проверяет нормативные ограничения всего нового модуля."""
        for path in ROOT.rglob("*.py"):
            relative = path.relative_to(ROOT)
            tree = ast.parse(path.read_text())
            if path.name == "__init__.py":
                self.assertEqual(path.read_text(), "")
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertIsNotNone(node.returns, str(relative))
                    for arg in [
                        *node.args.posonlyargs,
                        *node.args.args,
                        *node.args.kwonlyargs,
                        *([node.args.vararg] if node.args.vararg else []),
                        *([node.args.kwarg] if node.args.kwarg else []),
                    ]:
                        if arg.arg not in {"self", "cls"}:
                            self.assertIsNotNone(
                                arg.annotation, f"{relative}: {arg.arg}"
                            )
                    self.assertTrue(ast.get_docstring(node), f"{relative}: {node.name}")
                    if node.name == "__post_init__":
                        self.assertIn("value_object", relative.parts)
                if isinstance(node, ast.ClassDef):
                    self.assertTrue(ast.get_docstring(node), f"{relative}: {node.name}")
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                if isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                if relative.parts[0] in {"domain", "application"}:
                    for name in names:
                        self.assertFalse(
                            name.startswith(
                                (
                                    "sqlalchemy",
                                    "fastapi",
                                    "pydantic",
                                    "minio",
                                    "src.config",
                                    "src.modules.files.infrastructure",
                                    "src.modules.files.presentation",
                                    "src.modules.shared.infrastructure",
                                    "src.modules.shared.presentation",
                                )
                            ),
                            f"{relative}: {name}",
                        )
                        if relative.parts[0] == "domain":
                            self.assertFalse(
                                name.startswith("src.modules.files.application")
                            )
                if (
                    (
                        relative.parts[0] == "application"
                        or "persistence" in relative.parts
                    )
                    and isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                ):
                    self.assertNotIn(
                        node.func.attr, {"commit", "rollback"}, str(relative)
                    )
            if relative.parts[0] == "domain" and path.name == "aggregate.py":
                methods = {
                    n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                }
                self.assertTrue({"create", "restore"} <= methods)
            if path.name.endswith("mapper.py"):
                self.assertFalse(any(isinstance(n, ast.Await) for n in ast.walk(tree)))

    def test_http_is_read_only_and_has_separate_contracts(self) -> None:
        """Отсутствуют download, upload, публичные URL и фиктивные request schemas."""
        for root, scenario in [
            ("storage_provider", "list_providers"),
            ("bucket", "list_buckets"),
        ]:
            folder = ROOT / "presentation" / root
            self.assertTrue((folder / "http/controller" / f"{scenario}.py").exists())
            self.assertTrue((folder / "http/response" / f"{scenario}.py").exists())
            self.assertFalse((folder / "http/request").exists())
            tree = ast.parse((folder / "router.py").read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword) and node.arg == "methods":
                    self.assertEqual(ast.literal_eval(node.value), ["GET"])
        for path in ROOT.rglob("*.py"):
            self.assertNotIn("presigned_get_object(", path.read_text())
            self.assertNotIn("presigned_put_object(", path.read_text())

    def test_compose_storage_is_private_and_lifecycle_worker_can_reach_it(self) -> None:
        """Dev-порты доступны только localhost; Instance override закрывает MinIO."""
        import yaml

        project = ROOT.parents[2]
        base = yaml.safe_load((project / "docker-compose.yml").read_text())
        self.assertTrue(
            all(
                port.startswith("127.0.0.1:")
                for port in base["services"]["minio"]["ports"]
            )
        )
        self.assertTrue(base["networks"]["file-storage"]["internal"])
        self.assertEqual(base["services"]["minio"]["networks"], ["file-storage"])
        # BaseLoader допускает Compose !reset без выполнения interpolation/env_file.
        overlay = yaml.load(
            (project / "docker-compose.control-plane.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        self.assertEqual(overlay["services"]["minio"]["ports"], [])
        for name in ("api", "lifecycle-worker"):
            self.assertIn("file-storage", overlay["services"][name]["networks"])
        self.assertEqual(
            overlay["x-integration-environment"]["FILES__ENDPOINT"], "minio:9000"
        )
