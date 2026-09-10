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
    def test_removed_dynamic_modules_have_no_imports(self) -> None:
        for root in ("src", "test"):
            for path in iter_python_files(root):
                for module_name in iter_imports(path):
                    self.assertFalse(
                        module_name.startswith(
                            ("src.modules.schema_registry", "src.modules.runtime_data")
                        ),
                        msg=f"{path} imports removed module {module_name}",
                    )

    def test_inventory_domain_dependencies_point_inward(self) -> None:
        forbidden = (
            "sqlalchemy",
            "alembic",
            "fastapi",
            "pydantic",
            "src.modules.inventory.infrastructure",
            "src.modules.inventory.presentation",
            "src.modules.inventory.application",
            "src.modules.shared.infrastructure",
            "src.modules.shared.presentation",
            "src.modules.shared.application",
        )
        for path in iter_python_files("src/modules/inventory/domain"):
            for name in iter_imports(path):
                self.assertFalse(name.startswith(forbidden), f"{path} imports {name}")

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
            "src.modules.shared.presentation.email_sender",
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

    def test_email_delivery_does_not_use_app_state_or_identity_template_paths(
        self,
    ) -> None:
        paths = [
            PROJECT_ROOT / "src/modules/shared/presentation/email/depends.py",
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

    def test_business_modules_do_not_import_shared_event_bus_rabbitmq_adapter(
        self,
    ) -> None:
        forbidden_shared_adapter = "src.modules.shared.infrastructure.events.rabbitmq_integration_event_publisher"
        allowed_faststream_paths = {
            (
                PROJECT_ROOT
                / "src/modules/shared/infrastructure/events/rabbitmq_integration_event_publisher.py"
            ).resolve(),
            (
                PROJECT_ROOT
                / "src/modules/shared/infrastructure/events/rabbitmq_integration_event_console_worker.py"
            ).resolve(),
            (
                PROJECT_ROOT
                / "src/modules/shared/infrastructure/messaging/rabbitmq/broker_provider.py"
            ).resolve(),
            (
                PROJECT_ROOT
                / "src/modules/shared/infrastructure/messaging/rabbitmq/mapper.py"
            ).resolve(),
        }
        for path in iter_python_files("src/modules"):
            resolved_path = path.resolve()
            is_shared_path = "/src/modules/shared/" in path.as_posix()
            for module_name in iter_imports(path):
                if not is_shared_path:
                    self.assertNotEqual(
                        module_name,
                        forbidden_shared_adapter,
                        msg=f"{path} imports shared event bus RabbitMQ adapter directly",
                    )
                if module_name == "faststream.rabbit":
                    self.assertIn(
                        resolved_path,
                        allowed_faststream_paths,
                        msg=f"{path} imports faststream.rabbit outside approved adapters",
                    )

    def test_shared_legacy_directories_are_removed(self) -> None:
        removed_dirs = (
            "src/modules/shared/kernel",
            "src/modules/shared/db",
            "src/modules/shared/depends",
            "src/modules/shared/http",
        )
        for relative_path in removed_dirs:
            self.assertFalse(
                (PROJECT_ROOT / relative_path).exists(),
                msg=f"{relative_path} should not exist after shared layer refactor",
            )

    def test_shared_layer_import_direction_is_respected(self) -> None:
        forbidden_by_layer = {
            "domain": (
                "src.modules.shared.application",
                "src.modules.shared.infrastructure",
                "src.modules.shared.presentation",
            ),
            "application": (
                "src.modules.shared.infrastructure",
                "src.modules.shared.presentation",
            ),
            "infrastructure": ("src.modules.shared.presentation",),
        }
        for layer, forbidden_prefixes in forbidden_by_layer.items():
            for path in iter_python_files(f"src/modules/shared/{layer}"):
                for module_name in iter_imports(path):
                    self.assertFalse(
                        any(
                            module_name.startswith(prefix)
                            for prefix in forbidden_prefixes
                        ),
                        msg=f"{path} imports forbidden shared layer {module_name}",
                    )

    def test_events_management_command_uses_shared_rabbitmq_foundation(self) -> None:
        path = PROJECT_ROOT / "src/management/commands/events.py"
        content = path.read_text(encoding="utf-8")
        self.assertIn("src.modules.shared.presentation.events", content)
        self.assertIn("RabbitMQTopologyManager", content)
        self.assertIn("ensure_event_bus_topology", content)
        forbidden_patterns = (
            "RabbitMQIntegrationEventPublisher",
            "SqlAlchemyOutboxRepository",
            "UtcClock",
        )
        for pattern in forbidden_patterns:
            self.assertNotIn(
                pattern,
                content,
                msg=f"{path} should not assemble shared event infrastructure directly",
            )

    def test_rabbitbroker_is_created_only_in_shared_rabbitmq_provider(self) -> None:
        allowed_path = (
            PROJECT_ROOT
            / "src/modules/shared/infrastructure/messaging/rabbitmq/broker_provider.py"
        ).resolve()
        for path in iter_python_files("src"):
            content = path.read_text(encoding="utf-8")
            if "RabbitBroker(" not in content:
                continue
            self.assertEqual(
                path.resolve(),
                allowed_path,
                msg=f"{path} creates RabbitBroker outside shared provider",
            )

    def test_application_layers_do_not_import_rabbitmq_or_config(self) -> None:
        checked_roots = (
            "src/modules/shared/application/messaging",
            "src/modules/shared/application/events",
        )
        forbidden_prefixes = (
            "faststream",
            "faststream.rabbit",
            "src.config",
            "src.modules.shared.infrastructure.messaging",
        )
        for root in checked_roots:
            for path in iter_python_files(root):
                for module_name in iter_imports(path):
                    self.assertFalse(
                        any(
                            module_name.startswith(prefix)
                            for prefix in forbidden_prefixes
                        ),
                        msg=f"{path} imports forbidden application dependency {module_name}",
                    )

    def test_jobs_management_command_uses_shared_presentation_wiring(self) -> None:
        path = PROJECT_ROOT / "src/management/commands/jobs.py"
        content = path.read_text(encoding="utf-8")
        self.assertIn("src.modules.shared.presentation.jobs", content)
        forbidden_patterns = (
            "src.modules.shared.infrastructure.jobs",
            "SqlAlchemyScheduledJobRepository",
            "ScheduledJobModel",
            "UtcClock",
        )
        for pattern in forbidden_patterns:
            self.assertNotIn(
                pattern,
                content,
                msg=f"{path} should not assemble shared jobs infrastructure directly",
            )

    def test_business_modules_do_not_import_shared_jobs_infrastructure(self) -> None:
        forbidden_prefix = "src.modules.shared.infrastructure.jobs"
        allowed_paths = {
            (PROJECT_ROOT / "src/modules/persistence.py").resolve(),
        }
        for path in iter_python_files("src/modules"):
            if path.resolve() in allowed_paths:
                continue
            is_shared_path = "/src/modules/shared/" in path.as_posix()
            for module_name in iter_imports(path):
                if is_shared_path:
                    continue
                self.assertFalse(
                    module_name.startswith(forbidden_prefix),
                    msg=f"{path} imports shared jobs infrastructure directly",
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
            if "/src/modules/shared/domain/events/" in path.as_posix():
                continue
            if "/src/modules/shared/domain/jobs/" in path.as_posix():
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
