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

    def test_runtime_data_root_import_surface_is_not_used_in_source(self) -> None:
        forbidden_modules = {
            "src.modules.runtime_data",
            "src.modules.runtime_data.application",
            "src.modules.runtime_data.infrastructure",
            "src.modules.runtime_data.infrastructure.postgres",
            "src.modules.runtime_data.infrastructure.persistence.postgres",
            "src.modules.runtime_data.infrastructure.persistence.postgres.gateway",
        }
        for path in iter_python_files("src"):
            if path == PROJECT_ROOT / "src/modules/runtime_data/__init__.py":
                continue
            for module_name in iter_imports(path):
                self.assertNotIn(
                    module_name,
                    forbidden_modules,
                    msg=f"{path} imports runtime_data compatibility surface {module_name}",
                )

    def test_runtime_data_legacy_filter_specs_are_removed(self) -> None:
        forbidden_names = {
            "FilterSpec",
            "FilterGroupSpec",
            "FilterExpression",
            "PostgresRuntimeGateway",
        }
        for path in iter_python_files("src"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imported_names = {alias.name for alias in node.names}
                    self.assertFalse(
                        imported_names & forbidden_names,
                        msg=f"{path} imports removed runtime_data names {imported_names & forbidden_names}",
                    )
                elif isinstance(node, ast.ClassDef):
                    self.assertNotIn(
                        node.name,
                        forbidden_names,
                        msg=f"{path} defines removed runtime_data class {node.name}",
                    )

    def test_runtime_data_postgres_compatibility_shim_is_removed(self) -> None:
        self.assertFalse(
            (
                PROJECT_ROOT / "src/modules/runtime_data/infrastructure/postgres.py"
            ).exists(),
            msg="runtime_data PostgreSQL compatibility shim still exists.",
        )
        self.assertFalse(
            (
                PROJECT_ROOT
                / "src/modules/runtime_data/infrastructure/persistence/postgres/gateway/runtime_gateway.py"
            ).exists(),
            msg="PostgresRuntimeGateway facade still exists.",
        )

    def test_identity_use_case_callers_do_not_use_execute_style(self) -> None:
        forbidden_patterns = ("use_case.execute(", "_use_case.execute(")
        paths = [
            *iter_python_files(
                "src/modules/identity/presentation/http/console_auth/controller"
            ),
            PROJECT_ROOT
            / "src/modules/shared/presentation/identity_context/depends.py",
            PROJECT_ROOT
            / "src/modules/shared/presentation/identity_context/authenticate_by_session_use_case_adapter.py",
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

    def test_communication_does_not_use_public_persistence_models(self) -> None:
        persistence_path = (
            PROJECT_ROOT / "src/modules/communication/infrastructure/persistence.py"
        )
        self.assertFalse(
            persistence_path.exists(),
            msg="Communication public SQLAlchemy persistence models still exist.",
        )
        forbidden_import = "src.modules.communication.infrastructure.persistence"
        for root in ("src", "test"):
            for path in iter_python_files(root):
                for module_name in iter_imports(path):
                    self.assertNotEqual(
                        module_name,
                        forbidden_import,
                        msg=f"{path} imports removed communication persistence",
                    )

    def test_communication_application_does_not_import_infrastructure(self) -> None:
        forbidden_prefix = "src.modules.communication.infrastructure"
        for path in iter_python_files("src/modules/communication/application"):
            for module_name in iter_imports(path):
                self.assertFalse(
                    module_name.startswith(forbidden_prefix),
                    msg=f"{path} imports forbidden infrastructure module {module_name}",
                )

    def test_communication_does_not_import_contact_point(self) -> None:
        forbidden_prefix = "src.modules.contact_point"
        for path in iter_python_files("src/modules/communication"):
            for module_name in iter_imports(path):
                self.assertFalse(
                    module_name.startswith(forbidden_prefix),
                    msg=f"{path} imports forbidden contact_point module {module_name}",
                )

    def test_business_modules_do_not_import_shared_event_bus_rabbitmq_adapter(
        self,
    ) -> None:
        forbidden_shared_adapter = "src.modules.shared.infrastructure.events.rabbitmq_integration_event_publisher"
        allowed_faststream_paths = {
            (
                PROJECT_ROOT / "src/modules/communication/infrastructure/rabbitmq.py"
            ).resolve(),
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

    def test_shared_layer_roots_contain_only_init_files(self) -> None:
        shared_root = PROJECT_ROOT / "src/modules/shared"
        expected_layers = {"application", "domain", "infrastructure", "presentation"}
        self.assertEqual(
            {
                path.name
                for path in shared_root.iterdir()
                if path.is_dir() and path.name != "__pycache__"
            },
            expected_layers,
        )
        for layer in expected_layers:
            layer_root = shared_root / layer
            direct_files = {
                path.name for path in layer_root.iterdir() if path.is_file()
            }
            self.assertEqual(
                direct_files,
                {"__init__.py"},
                msg=f"{layer_root} should contain only __init__.py files directly",
            )

    def test_shared_files_live_under_feature_aggregates(self) -> None:
        allowed_aggregates = {
            "access",
            "email",
            "errors",
            "events",
            "http",
            "identity_context",
            "jobs",
            "messaging",
            "persistence",
            "time",
            "tokens",
            "uuid",
            "value_object",
        }
        shared_root = PROJECT_ROOT / "src/modules/shared"
        for layer in ("application", "domain", "infrastructure", "presentation"):
            layer_root = shared_root / layer
            for path in iter_python_files(f"src/modules/shared/{layer}"):
                relative = path.relative_to(layer_root)
                if relative.parts == ("__init__.py",):
                    continue
                self.assertGreaterEqual(
                    len(relative.parts),
                    2,
                    msg=f"{path} is not inside a shared feature aggregate",
                )
                self.assertIn(
                    relative.parts[0],
                    allowed_aggregates,
                    msg=f"{path} uses unknown shared aggregate {relative.parts[0]}",
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

    def test_shared_non_init_files_define_at_most_one_class(self) -> None:
        for path in iter_python_files("src/modules/shared"):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            classes = [
                node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]
            self.assertLessEqual(
                len(classes),
                1,
                msg=f"{path} defines multiple primary classes: {classes}",
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
            "src/modules/communication/application",
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

    def test_communication_http_root_router_is_composition_only(self) -> None:
        path = PROJECT_ROOT / "src/modules/communication/presentation/http/router.py"
        content = path.read_text(encoding="utf-8")
        self.assertNotIn("_raise_http_error", content)
        self.assertNotIn("asdict(", content)
        self.assertIn("include_router", content)

    def test_communication_controllers_map_responses_explicitly(self) -> None:
        forbidden_patterns = (
            ".__dict__",
            "ResponseSchema(**",
            "outbound_message_response(",
        )
        for path in iter_python_files("src/modules/communication/presentation/http"):
            is_controller = "/controller/" in path.as_posix()
            is_legacy_router_controller = (
                path.name == "router.py"
                and not path.as_posix().endswith("/presentation/http/router.py")
            )
            if not is_controller and not is_legacy_router_controller:
                continue
            content = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertNotIn(
                    pattern,
                    content,
                    msg=f"{path} should map HTTP responses explicitly in return blocks",
                )

    def test_communication_cleanup_removed_legacy_files(self) -> None:
        removed_files = (
            "src/modules/communication/application/dto.py",
            "src/modules/communication/application/use_cases.py",
            "src/modules/communication/application/ports.py",
            "src/modules/communication/infrastructure/repository.py",
            "src/modules/communication/infrastructure/message_template_runtime_repository.py",
        )
        for relative_path in removed_files:
            path = PROJECT_ROOT / relative_path
            self.assertFalse(
                path.exists(),
                msg=f"{path} should be removed after communication cleanup",
            )

    def test_communication_has_no_import_aliases(self) -> None:
        failures: list[str] = []
        for path in iter_python_files("src/modules/communication"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.asname:
                            failures.append(
                                f"{path}:{node.lineno} imports {alias.name} as {alias.asname}"
                            )
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.asname:
                            failures.append(
                                f"{path}:{node.lineno} imports {alias.name} as {alias.asname}"
                            )

        self.assertEqual(failures, [])

    def test_communication_has_no_forbidden_alias_assignments(self) -> None:
        forbidden_names = {
            "CommunicationRepositoryFactory",
            "ProviderConnection",
            "ProviderConnectorEntity",
            "ProviderMessageTypeEntity",
            "ProviderWebhookRepositoryProtocol",
            "SendCommunicationRepositoryProtocol",
        }
        failures: list[str] = []
        for path in iter_python_files("src/modules/communication"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
                    for target in node.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id in forbidden_names
                        ):
                            failures.append(f"{path}:{node.lineno} assigns {target.id}")
                if (
                    isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)
                    and isinstance(node.value, ast.Name)
                    and node.target.id in forbidden_names
                ):
                    failures.append(f"{path}:{node.lineno} assigns {node.target.id}")

        self.assertEqual(failures, [])

    def test_communication_repository_does_not_export_dto_mappers(self) -> None:
        path = PROJECT_ROOT / "src/modules/communication/infrastructure/repository.py"
        self.assertFalse(
            path.exists(),
            msg="Communication legacy runtime repository should be removed.",
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

    def test_schema_registry_object_feature_domain_has_clean_boundaries(self) -> None:
        forbidden_prefixes = (
            "src.modules.schema_registry.application",
            "src.modules.schema_registry.infrastructure",
            "src.modules.schema_registry.presentation",
        )
        for path in iter_python_files(
            "src/modules/schema_registry/domain/object_feature"
        ):
            for module_name in iter_imports(path):
                self.assertFalse(
                    any(
                        module_name.startswith(prefix) for prefix in forbidden_prefixes
                    ),
                    msg=f"{path} imports forbidden module {module_name}",
                )

    def test_schema_registry_object_feature_application_has_clean_boundaries(
        self,
    ) -> None:
        forbidden_prefixes = (
            "src.modules.schema_registry.infrastructure",
            "src.modules.schema_registry.presentation",
        )
        for path in iter_python_files(
            "src/modules/schema_registry/application/object_feature"
        ):
            for module_name in iter_imports(path):
                self.assertFalse(
                    any(
                        module_name.startswith(prefix) for prefix in forbidden_prefixes
                    ),
                    msg=f"{path} imports forbidden module {module_name}",
                )

    def test_schema_registry_object_feature_controllers_do_not_import_repositories_or_entities(
        self,
    ) -> None:
        forbidden_modules = {
            "src.modules.schema_registry.domain.object_feature.entity",
            "src.modules.schema_registry.domain.object_feature.repository",
            "src.modules.schema_registry.infrastructure.repository.object_feature_config_repository",
        }
        forbidden_names = (
            "ObjectFeatureConfigRepositoryDep",
            "ObjectFeatureConfigEntity",
        )
        for path in iter_python_files(
            "src/modules/schema_registry/presentation/http/object_feature/controller"
        ):
            for module_name in iter_imports(path):
                self.assertNotIn(
                    module_name,
                    forbidden_modules,
                    msg=f"{path} imports forbidden module {module_name}",
                )
            content = path.read_text(encoding="utf-8")
            for name in forbidden_names:
                self.assertNotIn(name, content, msg=f"{path} uses forbidden {name}")

    def test_schema_registry_object_feature_controller_files_have_one_endpoint(
        self,
    ) -> None:
        controller_dir = (
            PROJECT_ROOT
            / "src/modules/schema_registry/presentation/http/object_feature/controller"
        )
        for path in sorted(controller_dir.glob("*_controller.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            endpoint_count = 0
            for node in ast.walk(tree):
                if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr
                        in {"get", "post", "put", "patch", "delete"}
                    ):
                        endpoint_count += 1
            self.assertEqual(
                endpoint_count,
                1,
                msg=f"{path} should contain exactly one HTTP endpoint",
            )

    def test_schema_registry_object_feature_value_objects_are_split_by_file(
        self,
    ) -> None:
        base = PROJECT_ROOT / "src/modules/schema_registry/domain/object_feature"
        self.assertFalse(base.joinpath("value_object.py").exists())
        value_object_dir = base / "value_object"
        expected_files = {
            "__init__.py",
            "feature_code.py",
            "object_feature_code.py",
            "object_feature_config_id.py",
            "object_feature_kind.py",
            "object_feature_status.py",
        }
        self.assertEqual(
            {path.name for path in value_object_dir.glob("*.py")},
            expected_files,
        )
        for path in value_object_dir.glob("*.py"):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            classes = [
                node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]
            self.assertEqual(len(classes), 1, msg=f"{path} should define one class")

    def test_schema_registry_object_feature_has_no_mapper_files(self) -> None:
        removed_paths = (
            "src/modules/schema_registry/application/object_feature/mapper.py",
            "src/modules/schema_registry/application/object_feature/mapper",
            "src/modules/schema_registry/infrastructure/mapper/object_feature_config_orm_mapper.py",
            "src/modules/schema_registry/presentation/http/object_feature/mapper.py",
        )
        for relative_path in removed_paths:
            self.assertFalse(
                (PROJECT_ROOT / relative_path).exists(),
                msg=f"{relative_path} should not exist",
            )

    def test_schema_registry_object_feature_use_cases_have_protocols(self) -> None:
        self.assertFalse(
            (
                PROJECT_ROOT
                / "src/modules/schema_registry/application/object_feature/port/use_case.py"
            ).exists(),
            msg="object_feature use case protocols should live in use case files.",
        )
        expected_protocols = {
            "enable_object_feature_use_case.py": "EnableObjectFeatureUseCaseProtocol",
            "disable_object_feature_use_case.py": "DisableObjectFeatureUseCaseProtocol",
            "update_object_feature_config_use_case.py": "UpdateObjectFeatureConfigUseCaseProtocol",
            "get_object_feature_config_use_case.py": "GetObjectFeatureConfigUseCaseProtocol",
            "list_object_features_use_case.py": "ListObjectFeaturesUseCaseProtocol",
            "assert_object_feature_enabled_use_case.py": "AssertObjectFeatureEnabledUseCaseProtocol",
        }
        base_path = (
            PROJECT_ROOT
            / "src/modules/schema_registry/application/object_feature/use_case"
        )
        for file_name, protocol_name in expected_protocols.items():
            content = base_path.joinpath(file_name).read_text(encoding="utf-8")
            self.assertIn(
                f"class {protocol_name}(Protocol):",
                content,
                msg=f"{protocol_name} is missing from {file_name}",
            )

    def test_schema_registry_object_feature_use_cases_do_not_import_each_other(
        self,
    ) -> None:
        for path in iter_python_files(
            "src/modules/schema_registry/application/object_feature/use_case"
        ):
            if path.name == "__init__.py":
                continue
            for module_name in iter_imports(path):
                self.assertFalse(
                    module_name.startswith(
                        "src.modules.schema_registry.application.object_feature.use_case."
                    ),
                    msg=f"{path} imports another object_feature use case {module_name}",
                )

    def test_schema_registry_object_feature_uses_contact_point_code(self) -> None:
        for path in iter_python_files("src/modules/schema_registry"):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "CONTACT_POINTS",
                content,
                msg=f"{path} still uses legacy CONTACT_POINTS feature code",
            )
