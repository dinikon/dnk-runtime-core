from __future__ import annotations

import unittest

from src.modules.communication.presentation.http.router import router


class CommunicationHttpRouterTests(unittest.TestCase):
    def test_router_exposes_mvp_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(
            ("POST", "/communication/providers/connectors/import-yaml"), routes
        )
        self.assertIn(("GET", "/communication/providers/connectors"), routes)
        self.assertIn(("POST", "/communication/providers/connections"), routes)
        self.assertIn(("GET", "/communication/providers/connections"), routes)
        self.assertIn(("POST", "/communication/templates"), routes)
        self.assertIn(
            ("POST", "/communication/templates/{template_id}/versions"), routes
        )
        self.assertIn(
            (
                "POST",
                "/communication/templates/{template_id}/versions/{version_id}/activate",
            ),
            routes,
        )
        self.assertIn(("GET", "/communication/templates"), routes)
        self.assertIn(("POST", "/communication/send"), routes)
        self.assertIn(("GET", "/communication/messages"), routes)
        self.assertIn(("GET", "/communication/messages/{outbound_message_id}"), routes)
        self.assertIn(("POST", "/communication/webhooks/{provider_code}"), routes)


__all__ = ["CommunicationHttpRouterTests"]
