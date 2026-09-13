import unittest
from fastapi import FastAPI, Depends, Request, Response
from httpx import AsyncClient, ASGITransport
from src.modules.identity.presentation.http.csrf import issue_csrf, require_csrf
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.infrastructure.tokens import InMemoryTokenBackend


class BrowserCsrfTests(unittest.IsolatedAsyncioTestCase):
    async def test_host_origin_and_session_binding_and_secure_cookie(self):
        app = FastAPI()
        app.state.token_manager = TokenManager(InMemoryTokenBackend())

        @app.get("/csrf")
        async def csrf(request: Request, response: Response, tokens: TokenManagerDep):
            return await issue_csrf(request, response, tokens)

        @app.post("/change", dependencies=[Depends(require_csrf)])
        async def change():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://tenant.example"
        ) as client:
            response = await client.get("/csrf")
            cookie = response.headers["set-cookie"]
            self.assertIn("Secure", cookie)
            self.assertIn("HttpOnly", cookie)
            self.assertNotIn("Domain=", cookie)
            token = response.json()["csrf_token"]
            headers = {"Origin": "https://tenant.example", "X-CSRF-Token": token}
            self.assertEqual(
                (await client.post("/change", json={}, headers=headers)).status_code,
                200,
            )
            self.assertEqual(
                (
                    await client.post(
                        "/change",
                        json={},
                        headers={**headers, "Origin": "https://sibling.example"},
                    )
                ).status_code,
                403,
            )
            self.assertEqual((await client.post("/change", json={})).status_code, 403)
            client.cookies.set(
                "dnk_session", "new-session", domain="tenant.example", path="/"
            )
            self.assertEqual(
                (await client.post("/change", json={}, headers=headers)).status_code,
                403,
            )
            response = await client.get("/csrf")
            headers["X-CSRF-Token"] = response.json()["csrf_token"]
            self.assertEqual(
                (await client.post("/change", json={}, headers=headers)).status_code,
                200,
            )

    async def test_new_read_endpoints_return_404_for_unknown_host(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        from src.modules.identity.presentation.http.integration import (
            router,
            cloud_router,
        )
        from src.modules.identity.presentation.depends.integration import (
            get_access_service,
            get_cloud_service,
        )
        from src.modules.tenancy.domain.tenant_domain import TenantHostNotFoundError

        local = SimpleNamespace(
            context=AsyncMock(side_effect=TenantHostNotFoundError("missing.example"))
        )
        cloud = SimpleNamespace(
            callback=AsyncMock(side_effect=TenantHostNotFoundError("missing.example")),
            local=SimpleNamespace(uow=AsyncMock()),
        )
        app = FastAPI()
        app.include_router(router)
        app.include_router(cloud_router)
        app.state.token_manager = TokenManager(InMemoryTokenBackend())
        app.dependency_overrides[get_access_service] = lambda: local
        app.dependency_overrides[get_cloud_service] = lambda: cloud
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://missing.example"
        ) as client:
            csrf = await client.get("/api/console/auth/csrf")
            self.assertEqual(csrf.status_code, 404)
            self.assertNotIn("set-cookie", csrf.headers)
            callback = await client.get(
                "/api/auth/cloud/callback/?state=one&code=code&iss=https://core.example"
            )
            self.assertEqual(callback.status_code, 404)
            self.assertNotIn("location", callback.headers)
            cloud.local.uow.rollback.assert_awaited_once()
