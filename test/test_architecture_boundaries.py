from __future__ import annotations

import ast
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def iter_python_files(relative_dir: str) -> list[Path]:
    return sorted((PROJECT_ROOT / relative_dir).rglob("*.py"))


def iter_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    return imports


class ArchitectureBoundariesTests(unittest.TestCase):
    def test_no_modules_namespace_imports_are_used(self) -> None:
        forbidden_prefix = "modules."
        for root in ("src", "test"):
            for path in iter_python_files(root):
                for module_name in iter_imports(path):
                    self.assertFalse(
                        module_name.startswith(forbidden_prefix),
                        msg=f"{path} imports forbidden namespace {module_name}",
                    )

    def test_tenancy_application_does_not_import_schema_registry_application(
        self,
    ) -> None:
        forbidden_prefix = "src.modules.schema_registry.application"
        for path in iter_python_files("src/modules/tenancy/application"):
            for module_name in iter_imports(path):
                self.assertFalse(
                    module_name.startswith(forbidden_prefix),
                    msg=f"{path} imports forbidden module {module_name}",
                )

    def test_schema_registry_domain_stays_free_of_postgres_and_migration_impl(
        self,
    ) -> None:
        forbidden_prefixes = (
            "sqlalchemy",
            "src.modules.schema_registry.infrastructure.postgres",
            "src.modules.schema_registry.application.migration",
        )
        for path in iter_python_files("src/modules/schema_registry/domain"):
            for module_name in iter_imports(path):
                self.assertFalse(
                    any(
                        module_name.startswith(prefix) for prefix in forbidden_prefixes
                    ),
                    msg=f"{path} imports forbidden module {module_name}",
                )

    def test_legacy_paths_are_unused_in_source_and_tests(self) -> None:
        forbidden_prefixes = (
            "src.modules.schema_registry.domain.migration",
            "src.modules.schema_registry.domain.service.schema_registry_metadata_read_service",
            "src.modules.schema_registry.domain.service.schema_registry_metadata_write_service",
            "src.modules.schema_registry.domain.service.schema_registry_metadata_snapshot",
            "src.modules.schema_registry.domain.field.service",
            "src.modules.schema_registry.domain.field.enum.sql_type_preset",
            "src.modules.tenancy.application.commands",
            "src.modules.tenancy.application.dto",
            "src.modules.tenancy.application.queries",
            "src.modules.tenancy.application.use_cases",
            "src.modules.tenancy.domain.entities",
            "src.modules.tenancy.domain.errors",
            "src.modules.tenancy.domain.repositories",
            "src.modules.tenancy.domain.services",
            "src.modules.tenancy.domain.value_objects",
            "src.modules.tenancy.infrastructure.identity_provisioning",
            "src.modules.tenancy.infrastructure.mappers",
            "src.modules.tenancy.infrastructure.repositories",
            "src.modules.tenancy.presentation.http.admin_tenants",
            "src.modules.tenancy.presentation.http.console_tenants",
            "src.modules.tenancy.presentation.http.requests.admin_tenants",
            "src.modules.tenancy.presentation.http.responses.admin_tenants",
            "src.modules.tenancy.presentation.http.responses.console_tenants",
            "src.modules.identity.application.auth.services",
            "src.modules.identity.application.auth.use_cases",
            "src.modules.identity.application.auth.ports",
            "src.modules.identity.application.provisioning",
            "src.modules.identity.presentation.api",
            "src.modules.identity.presentation.depends.repositories",
            "src.modules.identity.presentation.depends.services",
            "src.modules.identity.presentation.depends.auth_repositories",
            "src.modules.identity.presentation.depends.auth_services",
            "src.modules.identity.presentation.depends.auth_use_cases",
            "src.modules.identity.presentation.http.console_auth.controller.error_mapper",
            "src.modules.identity.infrastructure.mapper",
        )
        forbidden_modules = {
            "src.modules.identity.application.auth.dto",
            "src.modules.identity.domain.entities",
            "src.modules.identity.domain.errors",
            "src.modules.identity.infrastructure.repositories",
        }
        for root in ("src", "test"):
            for path in iter_python_files(root):
                for module_name in iter_imports(path):
                    self.assertFalse(
                        module_name in forbidden_modules
                        or any(
                            module_name.startswith(prefix)
                            for prefix in forbidden_prefixes
                        ),
                        msg=f"{path} still uses legacy path {module_name}",
                    )

    def test_identity_use_case_callers_do_not_use_execute_style(self) -> None:
        forbidden_patterns = ("use_case.execute(", "_use_case.execute(")
        paths = [
            *iter_python_files(
                "src/modules/identity/presentation/http/console_auth/controller"
            ),
            PROJECT_ROOT / "src/modules/shared/depends/authentication.py",
            PROJECT_ROOT / "test/test_identity_use_cases.py",
            PROJECT_ROOT / "test/test_identity_http_router.py",
        ]
        for path in paths:
            content = path.read_text(encoding="utf-8")
            self.assertFalse(
                any(pattern in content for pattern in forbidden_patterns),
                msg=f"{path} still uses execute-style identity use case calls",
            )
