from __future__ import annotations

import unittest

from src.modules.schema_registry.presentation.http.router import router


class SchemaConfigHttpRouterTests(unittest.TestCase):
    def test_router_exposes_config_schema_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/config/objects/list"), routes)
        self.assertIn(("POST", "/config/objects/create"), routes)
        self.assertIn(("DELETE", "/config/objects/delete"), routes)
        self.assertIn(("POST", "/config/objects/schema"), routes)
        self.assertIn(("POST", "/config/objects/fields/create"), routes)
        self.assertIn(("DELETE", "/config/objects/fields/delete"), routes)


__all__ = ["SchemaConfigHttpRouterTests"]
