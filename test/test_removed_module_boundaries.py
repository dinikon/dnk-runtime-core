from __future__ import annotations

import unittest
from pathlib import Path

import httpx

from src.app_factory import create_app
from src.config import dnk_config
from src.management.cli import build_parser
from src.modules.shared.infrastructure.persistence import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RemovedModuleBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def test_dynamic_modules_and_surfaces_are_absent(self) -> None:
        self.assertFalse((PROJECT_ROOT / "src/modules/schema_registry").exists())
        self.assertFalse((PROJECT_ROOT / "src/modules/runtime_data").exists())
        self.assertNotIn("schema-registry", build_parser().format_help())
        self.assertFalse(hasattr(dnk_config, "DEFAULT_SEED_MODULE"))
        paths = create_app().openapi()["paths"]
        self.assertFalse(any(path.startswith("/api/console/config/") for path in paths))
        self.assertNotIn("data_sources", Base.metadata.tables)

    async def test_workflow_and_communication_are_absent(self) -> None:
        removed_paths = (
            "src/modules/workflow",
            "src/modules/communication",
            "src/management/commands/communication.py",
            "src/config/infrastructure/communication_queue_config.py",
            "src/modules/schema_registry/seed/contexts/workflow.py",
            "src/modules/schema_registry/seed/contexts/communication.py",
            "frontends/apps/console/src/modules/workflow",
            "frontends/apps/console/src/modules/communication",
        )
        for relative_path in removed_paths:
            self.assertFalse((PROJECT_ROOT / relative_path).exists())

        app = create_app()
        openapi_paths = set(app.openapi()["paths"])
        removed_route_prefixes = (
            "/api/console/workflows",
            "/api/console/communication",
        )
        for prefix in removed_route_prefixes:
            self.assertFalse(any(path.startswith(prefix) for path in openapi_paths))

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            workflow_response = await client.get("/api/console/workflows")
            communication_response = await client.get(
                "/api/console/communication/messages"
            )

        self.assertEqual(workflow_response.status_code, 404)
        self.assertEqual(communication_response.status_code, 404)
        self.assertFalse(hasattr(dnk_config, "COMMUNICATION_QUEUE"))
        self.assertNotIn("communication", build_parser().format_help())

    async def test_custom_object_and_configuration_routes_are_absent(
        self,
    ) -> None:
        self.assertFalse((PROJECT_ROOT / "src/modules/custom_object").exists())

        app = create_app()
        openapi_paths = set(app.openapi()["paths"])
        self.assertFalse(
            any(
                path.startswith("/api/console/custom-objects/records")
                for path in openapi_paths
            )
        )
        self.assertFalse(
            {
                "/api/console/config/objects/list",
                "/api/console/config/objects/create",
                "/api/console/config/objects/delete",
                "/api/console/config/objects/schema",
            }.issubset(openapi_paths)
        )

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/console/custom-objects/records/list",
                json={},
            )

        self.assertEqual(response.status_code, 404)

    async def test_contact_point_and_object_feature_are_absent(self) -> None:
        removed_paths = (
            "src/modules/contact_point",
            "src/modules/schema_registry/application/object_feature",
            "src/modules/schema_registry/domain/object_feature",
            "src/modules/schema_registry/presentation/http/object_feature",
            "src/modules/schema_registry/infrastructure/persistence/object_feature_config.py",
            "src/modules/schema_registry/infrastructure/repository/object_feature_config_repository.py",
        )
        for relative_path in removed_paths:
            self.assertFalse((PROJECT_ROOT / relative_path).exists())

        app = create_app()
        openapi_paths = set(app.openapi()["paths"])
        removed_route_prefixes = (
            "/api/console/contact-points",
            "/api/console/config/objects/features",
        )
        for prefix in removed_route_prefixes:
            self.assertFalse(any(path.startswith(prefix) for path in openapi_paths))

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            contact_point_response = await client.post(
                "/api/console/contact-points/attach",
                json={},
            )
            object_feature_response = await client.post(
                "/api/console/config/objects/features/list",
                json={},
            )

        self.assertEqual(contact_point_response.status_code, 404)
        self.assertEqual(object_feature_response.status_code, 404)
        self.assertNotIn("object_feature_config", Base.metadata.tables)

    async def test_crm_module_and_http_surface_are_absent(self) -> None:
        self.assertFalse((PROJECT_ROOT / "src/modules/crm").exists())

        app = create_app()
        openapi_paths = set(app.openapi()["paths"])
        self.assertFalse(
            any(path.startswith("/api/console/crm/") for path in openapi_paths)
        )

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            contacts_response = await client.get("/api/console/crm/contacts")
            companies_response = await client.get("/api/console/crm/companies")

        self.assertEqual(contacts_response.status_code, 404)
        self.assertEqual(companies_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
