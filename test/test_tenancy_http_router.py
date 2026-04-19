from __future__ import annotations

import unittest

from src.modules.tenancy.presentation.http.router import router


class TenancyHttpRouterTests(unittest.TestCase):
    def test_router_keeps_public_tenancy_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/admin/create-tenant"), routes)
        self.assertIn(("GET", "/console/tenants/resolve"), routes)


__all__ = ["TenancyHttpRouterTests"]
