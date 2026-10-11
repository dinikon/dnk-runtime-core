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
    "stored_file/query/list_files": "ListFilesResultDTO",
    "stored_file/query/list_trashed_files": "ListTrashedFilesResultDTO",
    "stored_file/query/get_files_overview": "GetFilesOverviewResultDTO",
    "stored_file/command/trash_file": "TrashFileResultDTO",
    "stored_file/command/restore_file": "RestoreFileResultDTO",
    "stored_file/command/request_file_purge": "None",
    "stored_file/command/purge_file": "None",
    "stored_file/command/cleanup_expired_trash": "CleanupExpiredTrashResultDTO",
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

    def test_http_has_explicit_method_whitelist_and_separate_contracts(self) -> None:
        """Семь сценариев StoredFile разделены; нет download, presigned и пустых schemas."""
        for root, scenarios in {
            "storage_provider": [("list_providers", True, False)],
            "bucket": [("list_buckets", True, False)],
            "stored_file": [
                ("list_files", True, False),
                ("list_trashed_files", True, False),
                ("get_files_overview", True, False),
                ("upload_file", True, True),
                ("trash_file", True, False),
                ("restore_file", True, False),
                ("request_file_purge", False, False),
            ],
        }.items():
            folder = ROOT / "presentation" / root
            for scenario, response, request in scenarios:
                self.assertTrue(
                    (folder / "http/controller" / f"{scenario}.py").exists()
                )
                self.assertEqual(
                    (folder / "http/response" / f"{scenario}.py").exists(), response
                )
                self.assertEqual(
                    (folder / "http/request" / f"{scenario}.py").exists(), request
                )
            tree = ast.parse((folder / "router.py").read_text())
            routes = {}
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_api_route"
                ):
                    kwargs = {item.arg: item.value for item in node.keywords}
                    path = ast.literal_eval(node.args[0])
                    methods = tuple(ast.literal_eval(kwargs["methods"]))
                    routes[(path, methods)] = kwargs
                    dependencies = ast.unparse(kwargs["dependencies"])
                    if methods != ("GET",):
                        self.assertIn("Depends(require_csrf)", dependencies)
                    else:
                        self.assertIn(
                            "Depends(require_files_admin_context)", dependencies
                        )
            if root == "stored_file":
                self.assertEqual(
                    set(routes),
                    {
                        ("/files/items/", ("GET",)),
                        ("/files/trash/", ("GET",)),
                        ("/files/overview/", ("GET",)),
                        ("/files/items/", ("POST",)),
                        ("/files/items/{file_id}/", ("DELETE",)),
                        ("/files/items/{file_id}/restore/", ("POST",)),
                        ("/files/trash/{file_id}/", ("DELETE",)),
                    },
                )
                purge = routes[("/files/trash/{file_id}/", ("DELETE",))]
                self.assertEqual(ast.literal_eval(purge["status_code"]), 202)
                self.assertEqual(ast.literal_eval(purge["response_model"]), None)
        for path in ROOT.rglob("*.py"):
            self.assertNotIn("presigned_get_object(", path.read_text())
            self.assertNotIn("presigned_put_object(", path.read_text())

    def test_file_read_projections_do_not_load_or_change_aggregates(self) -> None:
        """Read-side использует порт проекций, без фабрик агрегатов и write repository."""
        paths = [
            *ROOT.glob("application/stored_file/query/list_*/*.py"),
            *ROOT.glob("application/stored_file/query/get_files_overview/*.py"),
            ROOT / "infrastructure/stored_file/persistence/query_repository.py",
            ROOT / "infrastructure/stored_file/persistence/query_mapper.py",
        ]
        for path in paths:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn("domain.stored_file.aggregate", node.module)
                    self.assertNotIn("domain.stored_file.repository", node.module)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(
                        node.func.attr, {"to_domain", "mark_uploaded", "move_to_trash"}
                    )

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
        self.assertEqual(
            base["services"]["minio"]["networks"],
            ["file-storage", "file-storage-local"],
        )
        self.assertEqual(base["networks"]["file-storage-local"]["driver"], "bridge")
        self.assertFalse(base["networks"]["file-storage-local"].get("internal", False))
        for name, service in base["services"].items():
            if name != "minio":
                self.assertNotIn("file-storage-local", service.get("networks", []))
        # BaseLoader допускает Compose !reset без выполнения interpolation/env_file.
        overlay = yaml.load(
            (project / "docker-compose.control-plane.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        self.assertEqual(overlay["services"]["minio"]["ports"], [])
        self.assertEqual(overlay["services"]["minio"]["networks"], ["file-storage"])
        for name in ("api", "lifecycle-worker"):
            self.assertIn("file-storage", overlay["services"][name]["networks"])
        self.assertEqual(
            overlay["x-integration-environment"]["FILES__ENDPOINT"], "minio:9000"
        )
