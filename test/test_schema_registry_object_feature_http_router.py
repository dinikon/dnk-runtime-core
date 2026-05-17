from __future__ import annotations

import unittest

from src.modules.schema_registry.presentation.http.router import router


class SchemaRegistryObjectFeatureHttpRouterTests(unittest.TestCase):
    def test_router_exposes_object_feature_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/config/objects/features/enable"), routes)
        self.assertIn(("POST", "/config/objects/features/disable"), routes)
        self.assertIn(("POST", "/config/objects/features/update"), routes)
        self.assertIn(("POST", "/config/objects/features/schema"), routes)
        self.assertIn(("POST", "/config/objects/features/list"), routes)


__all__ = ["SchemaRegistryObjectFeatureHttpRouterTests"]
