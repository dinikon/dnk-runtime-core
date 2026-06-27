from __future__ import annotations

import unittest
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.tenancy.application.tenant_domain.dto import (
    ResolveTenantByHostResultDTO,
)
from src.modules.tenancy.presentation.depends.application import (
    get_resolve_tenant_by_host_use_case,
)
from src.modules.tenancy.presentation.http.router import router


class _ResolveTenantUseCaseStub:
    def __init__(self, result: ResolveTenantByHostResultDTO) -> None:
        self.result = result

    async def execute(self, query) -> ResolveTenantByHostResultDTO:
        return self.result


class TenancyHttpRouterTests(unittest.TestCase):
    def test_router_keeps_public_tenancy_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/admin/create-tenant"), routes)
        self.assertIn(("GET", "/console/tenants/resolve"), routes)

    def test_resolve_tenant_response_includes_tenant_name(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api")
        tenant_id = UUID("11111111-1111-1111-1111-111111111111")
        app.dependency_overrides[get_resolve_tenant_by_host_use_case] = lambda: (
            _ResolveTenantUseCaseStub(
                ResolveTenantByHostResultDTO(
                    exists=True,
                    available=True,
                    status="active",
                    tenant_id=tenant_id,
                    tenant_name="Acme",
                    api_host="api.example.com",
                )
            )
        )

        response = TestClient(app).get(
            "/api/console/tenants/resolve",
            headers={"host": "console.example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tenant_name"], "Acme")

    def test_resolve_tenant_not_found_response_has_null_tenant_name(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_resolve_tenant_by_host_use_case] = lambda: (
            _ResolveTenantUseCaseStub(
                ResolveTenantByHostResultDTO(
                    exists=False,
                    available=False,
                    status="not_found",
                    tenant_id=None,
                    tenant_name=None,
                    api_host=None,
                )
            )
        )

        response = TestClient(app).get(
            "/api/console/tenants/resolve",
            headers={"host": "missing.example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["tenant_name"])


__all__ = ["TenancyHttpRouterTests"]
