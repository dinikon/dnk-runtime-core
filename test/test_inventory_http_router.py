from __future__ import annotations

import unittest

from src.modules.inventory.presentation.http.router import router


class InventoryHttpRouterTests(unittest.TestCase):
    def test_router_keeps_public_inventory_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/inventory/products"), routes)
        self.assertIn(("POST", "/inventory/products/fields"), routes)
        self.assertIn(("GET", "/inventory/products"), routes)
        self.assertIn(("GET", "/inventory/products/{product_id}"), routes)
        self.assertIn(("PUT", "/inventory/products/{product_id}"), routes)
        self.assertIn(("DELETE", "/inventory/products/{product_id}"), routes)
        self.assertIn(("POST", "/inventory/categories"), routes)
        self.assertIn(("POST", "/inventory/categories/fields"), routes)
        self.assertIn(("GET", "/inventory/categories"), routes)
        self.assertIn(("GET", "/inventory/categories/{category_id}"), routes)
        self.assertIn(("PUT", "/inventory/categories/{category_id}"), routes)
        self.assertIn(("DELETE", "/inventory/categories/{category_id}"), routes)


__all__ = ["InventoryHttpRouterTests"]
