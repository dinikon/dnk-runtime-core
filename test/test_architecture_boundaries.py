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
            "src.modules.identity.application.auth.service.login_otp_email_composer",
            "src.modules.identity.infrastructure.adapter.login_otp_email_composer",
            "src.modules.shared.depends.email_sender",
        )
        forbidden_modules = {
            "src.modules.identity.application.auth.dto",
            "src.modules.identity.domain.entities",
            "src.modules.identity.domain.errors",
            "src.modules.identity.infrastructure.repositories",
            "src.modules.identity.application.ports.email_sender",
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

    def test_email_delivery_does_not_use_app_state_or_identity_template_paths(
        self,
    ) -> None:
        paths = [
            PROJECT_ROOT / "src/modules/shared/depends/email_service.py",
            PROJECT_ROOT
            / "src/modules/identity/presentation/depends/infrastructure.py",
            PROJECT_ROOT
            / "src/modules/identity/application/auth/use_case/request_email_otp.py",
        ]
        forbidden_patterns = (
            "request.app.state",
            "login_otp_email_composer",
            "email_templates",
            "FileLoginOtpEmailComposer",
        )
        for path in paths:
            content = path.read_text(encoding="utf-8")
            self.assertFalse(
                any(pattern in content for pattern in forbidden_patterns),
                msg=f"{path} still uses removed email wiring pattern",
            )

    def test_client_data_wiring_does_not_resolve_tenant_id(self) -> None:
        paths = [
            PROJECT_ROOT / "src/modules/crm/presentation/depends/infrastructure.py",
            PROJECT_ROOT
            / "src/modules/inventory/presentation/depends/infrastructure.py",
            PROJECT_ROOT
            / "src/modules/custom_object/presentation/depends/infrastructure.py",
        ]
        for path in paths:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "tenant_id",
                content,
                msg=f"{path} still resolves tenant_id in wiring",
            )

    def test_shared_exports_only_generic_entity_id_vo(self) -> None:
        paths = [
            PROJECT_ROOT / "src/modules/shared/__init__.py",
            PROJECT_ROOT / "src/modules/shared/domain/__init__.py",
            PROJECT_ROOT / "src/modules/shared/domain/value_object/__init__.py",
            PROJECT_ROOT / "src/modules/shared/domain/value_object/entity_id.py",
        ]
        for path in paths:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "TenantIdVO",
                content,
                msg=f"{path} exports or defines a tenant-specific id VO",
            )

        tree = ast.parse(
            (
                PROJECT_ROOT / "src/modules/shared/domain/value_object/entity_id.py"
            ).read_text(encoding="utf-8")
        )
        id_classes = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.endswith("IdVO")
        ]
        self.assertEqual(id_classes, ["EntityIdVO"])

    def test_concrete_id_value_objects_live_near_domain_objects(self) -> None:
        for path in iter_python_files("src/modules"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for class_def in ast.walk(tree):
                if not isinstance(class_def, ast.ClassDef):
                    continue
                if (
                    not class_def.name.endswith("IdVO")
                    or class_def.name == "EntityIdVO"
                ):
                    continue
                self.assertIn(
                    "/domain/",
                    path.as_posix(),
                    msg=f"{path}:{class_def.name} is not under module/domain",
                )
                self.assertIn(
                    "/value_object/",
                    path.as_posix(),
                    msg=f"{path}:{class_def.name} is not under value_object",
                )

    def test_custom_object_wiring_does_not_use_tenant_domain_id(self) -> None:
        path = (
            PROJECT_ROOT
            / "src/modules/custom_object/presentation/depends/infrastructure.py"
        )
        content = path.read_text(encoding="utf-8")
        self.assertNotIn("TenantIdVO", content)
        self.assertNotIn("src.modules.tenancy.domain", content)

    def test_custom_object_does_not_own_schema_config_or_ddl(self) -> None:
        forbidden_patterns = (
            "src.modules.schema_registry.application.config.object",
            "src.modules.schema_registry.application.config.field",
            "src.modules.schema_registry.application.migration",
            "src.modules.schema_registry.application.ports.tenant_schema_executor",
            "src.modules.schema_registry.domain.datasource.service",
            "src.modules.schema_registry.domain.object.repository",
            "SchemaConfigRepository",
            "TenantSchemaExecutor",
            "ObjectRepositoryProtocol",
            "DataSourceService",
            "CreateTableOperation",
            "AddColumnOperation",
            "DropTableOperation",
            "DropColumnOperation",
        )
        for path in iter_python_files("src/modules/custom_object"):
            content = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertNotIn(
                    pattern,
                    content,
                    msg=f"{path} still owns schema config or DDL via {pattern}",
                )

    def test_removed_id_wrapper_types_are_not_used(self) -> None:
        removed_types = ("Typed" + "EntityIdVO",)
        for root in ("src", "test"):
            for path in iter_python_files(root):
                if path == Path(__file__).resolve():
                    continue
                content = path.read_text(encoding="utf-8")
                for removed_type in removed_types:
                    self.assertNotIn(
                        removed_type,
                        content,
                        msg=f"{path} still uses removed id type {removed_type}",
                    )

    def test_concrete_id_value_objects_inherit_entity_id_vo(self) -> None:
        value_object_paths = [
            path
            for path in iter_python_files("src/modules")
            if path.name.endswith("_id.py")
            and "/value_object/" in path.as_posix()
            and path.name != "entity_id.py"
        ]
        for path in value_object_paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            id_classes = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef) and node.name.endswith("IdVO")
            ]
            self.assertTrue(id_classes, msg=f"{path} defines no concrete id VO")
            for class_def in id_classes:
                bases = {
                    base.id for base in class_def.bases if isinstance(base, ast.Name)
                }
                self.assertIn(
                    "EntityIdVO",
                    bases,
                    msg=f"{path}:{class_def.name} does not inherit EntityIdVO",
                )

    def test_domain_entity_ids_do_not_use_raw_uuid_annotations(self) -> None:
        allowed_patterns = (
            "FieldTypeEnum.UUID",
            'UUID = "uuid"',
            "from uuid import UUID",
        )
        for path in iter_python_files("src/modules"):
            if "/domain/" not in path.as_posix():
                continue
            if path.as_posix().endswith(
                "src/modules/shared/domain/value_object/entity_id.py"
            ):
                continue
            content = path.read_text(encoding="utf-8")
            filtered = content
            for pattern in allowed_patterns:
                filtered = filtered.replace(pattern, "")
            self.assertNotIn(
                ": UUID",
                filtered,
                msg=f"{path} uses raw UUID annotation in domain",
            )
