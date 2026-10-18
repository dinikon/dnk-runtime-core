"""Invitation OTP HTTP responses honor the deployment environment."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.presentation.invitation.depends import (
    get_request_invitation_otp_handler,
)
from src.modules.identity.presentation.auth.providers import get_tenant_context_reader
from src.modules.identity.presentation.auth.http.csrf_router import (
    router as csrf_router,
)
from src.modules.identity.application.invitation.command.request_invitation_otp.dto import (
    RequestInvitationOtpResultDTO,
)
from src.modules.identity.application.invitation.command.request_invitation_otp.command import (
    RequestInvitationOtpCommand,
)
from src.modules.identity.presentation.invitation.http.router import router
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.infrastructure.tokens import InMemoryTokenBackend


class InvitationOtpHttpTests(unittest.IsolatedAsyncioTestCase):
    async def request_otp(self, environment):
        service = SimpleNamespace(
            get_by_host=AsyncMock(),
            execute=AsyncMock(
                return_value=RequestInvitationOtpResultDTO("challenge", 300, "123456")
            ),
        )
        app = FastAPI()
        app.include_router(router)
        app.include_router(csrf_router)
        app.state.token_manager = TokenManager(InMemoryTokenBackend())
        app.dependency_overrides[get_request_invitation_otp_handler] = lambda: service
        app.dependency_overrides[get_tenant_context_reader] = lambda: service
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="https://tenant.example",
        ) as client:
            csrf = await client.get("/api/console/auth/csrf")
            self.assertEqual(csrf.status_code, 200)
            with patch.object(dnk_config, "DEPLOY_ENV", environment):
                response = await client.post(
                    "/api/console/invitations/request-otp",
                    json={"invitation_token": "i" * 43},
                    headers={
                        "Origin": "https://tenant.example",
                        "X-CSRF-Token": csrf.json()["csrf_token"],
                    },
                )
        service.execute.assert_awaited_once_with(
            RequestInvitationOtpCommand("tenant.example", "i" * 43)
        )
        return response

    async def test_non_development_returns_challenge_without_email_code(self):
        for environment in ("PRODUCTION", "STAGING", "development", ""):
            with self.subTest(environment=environment):
                response = await self.request_otp(environment)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.json(), {"token": "challenge", "expires_in": 300}
                )

    async def test_development_returns_challenge_with_debug_code(self):
        response = await self.request_otp("DEVELOPMENT")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {"token": "challenge", "expires_in": 300, "code": "123456"},
        )
