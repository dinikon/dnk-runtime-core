from __future__ import annotations

import unittest

from src.modules.custom_object.presentation.http.router import router


class CustomObjectHttpRouterTests(unittest.TestCase):

    def test_router_keeps_only_record_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/custom-objects/records/create"), routes)
        self.assertIn(("POST", "/custom-objects/records/detail"), routes)
        self.assertIn(("POST", "/custom-objects/records/list"), routes)
        self.assertIn(("PATCH", "/custom-objects/records/update"), routes)
        self.assertIn(("PUT", "/custom-objects/records/update"), routes)
        self.assertIn(("DELETE", "/custom-objects/records/delete"), routes)
        self.assertNotIn(("POST", "/custom-objects/list"), routes)
        self.assertNotIn(("POST", "/custom-objects/create"), routes)
        self.assertNotIn(("DELETE", "/custom-objects/delete"), routes)
        self.assertNotIn(("POST", "/custom-objects/schema"), routes)
        self.assertNotIn(("POST", "/custom-objects/fields/create"), routes)
        self.assertNotIn(("DELETE", "/custom-objects/fields/delete"), routes)


__all__ = ["CustomObjectHttpRouterTests"]
