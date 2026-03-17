from __future__ import annotations

import importlib
import unittest

from fastapi.routing import APIRoute

MODULE_IMPORTS: tuple[str, ...] = (
    "src.modules.crm",
    "src.modules.crm.domain",
    "src.modules.crm.application",
    "src.modules.crm.infrastructure",
    "src.modules.crm.presentation",
    "src.modules.crm.presentation.http",
    "src.modules.crm.presentation.http.router",
    "src.modules.crm.presentation.depends.application",
    "src.modules.crm.presentation.depends.infrastructure",
    "src.modules.crm.presentation.depends.security",
    "src.modules.runtime_schema",
    "src.modules.runtime_schema.domain",
    "src.modules.runtime_schema.application",
    "src.modules.runtime_schema.infrastructure",
    "src.modules.runtime_schema.presentation",
    "src.modules.runtime_schema.presentation.http",
    "src.modules.runtime_schema.presentation.http.router",
    "src.modules.runtime_schema.presentation.depends.application",
    "src.modules.runtime_schema.presentation.depends.infrastructure",
    "src.modules.runtime_schema.presentation.depends.security",
    "src.modules.runtime_record",
    "src.modules.runtime_record.domain",
    "src.modules.runtime_record.application",
    "src.modules.runtime_record.infrastructure",
    "src.modules.runtime_record.presentation",
    "src.modules.runtime_record.presentation.http",
    "src.modules.runtime_record.presentation.http.router",
    "src.modules.runtime_record.presentation.depends.application",
    "src.modules.runtime_record.presentation.depends.infrastructure",
    "src.modules.runtime_record.presentation.depends.security",
)


class TestTask2Step1SmokeImports(unittest.TestCase):
    def test_step1_modules_are_importable(self) -> None:
        for module_path in MODULE_IMPORTS:
            with self.subTest(module_path=module_path):
                imported = importlib.import_module(module_path)
                self.assertIsNotNone(imported)

    def test_step1_routers_are_connected_to_api_router(self) -> None:
        from src.modules.router import router as api_router

        route_paths = {
            route.path
            for route in api_router.routes
            if isinstance(route, APIRoute)
        }

        self.assertIn("/api/crm/health", route_paths)
        self.assertIn("/api/crm/tenants/{tenant_id}/contacts", route_paths)
        self.assertIn("/api/crm/tenants/{tenant_id}/contacts/{contact_id}", route_paths)
        self.assertIn("/api/crm/tenants/{tenant_id}/companies", route_paths)
        self.assertIn("/api/crm/tenants/{tenant_id}/companies/{company_id}", route_paths)
        self.assertIn("/api/runtime-schema/health", route_paths)
        self.assertIn("/api/runtime-record/health", route_paths)


if __name__ == "__main__":
    unittest.main()
