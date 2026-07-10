from __future__ import annotations

import unittest
from pathlib import Path

import httpx

from src.app_factory import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RemovedModuleBoundaryTests(unittest.IsolatedAsyncioTestCase):
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
