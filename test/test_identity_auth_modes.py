"""Environment-controlled OTP delivery and automatic OIDC login contracts."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.config.feature.identity.auth_config import IdentityAuthSettings
from src.modules.identity.application.auth.command.request_email_otp.command import (
    RequestEmailOtpCommand,
)
from src.modules.identity.application.auth.command.request_email_otp.dto import (
    RequestEmailOtpResultDTO,
)
from src.modules.identity.application.auth.service.otp_service import OtpService
from src.modules.identity.application.cloud.command.start_cloud_auth.command import (
    StartCloudAuthCommand,
)
from src.modules.identity.application.cloud.command.start_cloud_auth.dto import (
    StartCloudAuthResultDTO,
)
from src.modules.identity.application.cloud.command.start_cloud_auth.handler import (
    StartCloudAuthHandler,
)
from src.modules.identity.application.invitation.command.request_invitation_otp.command import (
    RequestInvitationOtpCommand,
)
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.domain.user.aggregate import User
from src.modules.identity.presentation.auth.depends import get_request_email_otp_handler
from src.modules.identity.presentation.auth.http.controller.request_email_otp import (
    router as otp_router,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.cloud.depends import get_start_cloud_auth_handler
from src.modules.identity.presentation.cloud.http.router import router as cloud_router
from src.modules.identity.presentation.invitation.depends import (
    get_request_invitation_otp_handler,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.domain.email import EmailDeliveryError
from src.modules.shared.infrastructure.tokens import InMemoryTokenBackend


class OtpEnvironmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.context = SimpleNamespace(
            tenant_id=uuid4(), tenant_domain_id=uuid4(), host="tenant.example"
        )
        self.reader = AsyncMock()
        self.reader.get_by_host.return_value = self.context
        self.email = AsyncMock()
        self.settings = IdentityAuthSettings()
        self.otp = OtpService(6)
        self.tokens = TokenManager(InMemoryTokenBackend())

    async def test_login_delivery_and_result_follow_server_environment(self) -> None:
        user = User.create_tenant_admin(
            tenant_id=EntityIdVO.from_value(self.context.tenant_id),
            first_name="Test",
            last_name="User",
        )
        user.add_email("user@example.com", is_primary=True)
        users = AsyncMock()
        users.get_by_tenant_and_primary_email.return_value = user
        for environment in ("DEVELOPMENT", "PRODUCTION", "STAGING", "development", ""):
            with self.subTest(environment=environment):
                self.email.reset_mock()
                store = AsyncMock()
                with patch.object(dnk_config, "DEPLOY_ENV", environment):
                    handler = get_request_email_otp_handler(
                        self.reader, users, store, self.otp, self.email, self.settings
                    )
                result = await handler.execute(
                    RequestEmailOtpCommand("tenant.example", "user@example.com")
                )
                challenge = store.create_challenge.await_args.args[0]
                if environment == "DEVELOPMENT":
                    self.email.send.assert_not_awaited()
                    self.assertIsNotNone(result.code)
                    code = result.code
                else:
                    self.email.send.assert_awaited_once()
                    self.assertIsNone(result.code)
                    code = self.email.send.await_args.args[2]["otp_code"]
                self.assertTrue(
                    self.otp.verify_code(code=code, code_hash=challenge.code_hash)
                )
                self.assertEqual(result.token, challenge.token)

    async def test_invitation_delivery_and_result_follow_server_environment(
        self,
    ) -> None:
        invitations = AsyncMock()
        invitations.valid_invitation.return_value = SimpleNamespace(
            id=uuid4(), email="guest@example.com"
        )
        previous_token = None
        for environment in ("DEVELOPMENT", "PRODUCTION", "STAGING", "development", ""):
            with self.subTest(environment=environment):
                self.email.reset_mock()
                with patch.object(dnk_config, "DEPLOY_ENV", environment):
                    handler = get_request_invitation_otp_handler(
                        self.email,
                        invitations,
                        self.otp,
                        self.settings,
                        self.reader,
                        self.tokens,
                    )
                result = await handler.execute(
                    RequestInvitationOtpCommand("tenant.example", "invitation")
                )
                self.assertNotEqual(previous_token, result.token)
                previous_token = result.token
                if environment == "DEVELOPMENT":
                    self.email.send.assert_not_awaited()
                    self.assertIsNotNone(result.code)
                else:
                    self.email.send.assert_awaited_once()
                    self.assertIsNone(result.code)

    async def test_invitation_keeps_delivery_errors_in_production(self) -> None:
        invitations = AsyncMock()
        invitations.valid_invitation.return_value = SimpleNamespace(
            id=uuid4(), email="guest@example.com"
        )
        self.email.send.side_effect = EmailDeliveryError("Unavailable")
        with patch.object(dnk_config, "DEPLOY_ENV", "PRODUCTION"):
            handler = get_request_invitation_otp_handler(
                self.email,
                invitations,
                self.otp,
                self.settings,
                self.reader,
                self.tokens,
            )
        with self.assertRaises(EmailDeliveryError):
            await handler.execute(
                RequestInvitationOtpCommand("tenant.example", "invitation")
            )

    async def test_login_http_does_not_expose_codes_outside_development(self) -> None:
        app = FastAPI()
        app.include_router(otp_router, prefix="/api/console/auth")
        handler = SimpleNamespace(
            execute=AsyncMock(
                return_value=RequestEmailOtpResultDTO("otp-token", 300, "123456")
            )
        )
        app.dependency_overrides[get_request_email_otp_handler] = lambda: handler
        async with AsyncClient(
            transport=ASGITransport(app), base_url="https://tenant.example"
        ) as client:
            for environment in (
                "DEVELOPMENT",
                "PRODUCTION",
                "STAGING",
                "development",
                "",
            ):
                with (
                    self.subTest(environment=environment),
                    patch.object(dnk_config, "DEPLOY_ENV", environment),
                ):
                    response = await client.post(
                        "/api/console/auth/request-otp",
                        json={"email": "user@example.com"},
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        "code" in response.json(), environment == "DEVELOPMENT"
                    )


class CloudStartTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_preserves_manual_default_and_allows_silent_login_only(
        self,
    ) -> None:
        app = FastAPI()
        app.include_router(cloud_router)
        app.dependency_overrides[require_csrf] = lambda: None
        handler = SimpleNamespace(
            execute=AsyncMock(
                return_value=StartCloudAuthResultDTO("https://core.example/authorize")
            )
        )
        app.dependency_overrides[get_start_cloud_auth_handler] = lambda: handler
        async with AsyncClient(
            transport=ASGITransport(app), base_url="https://tenant.example"
        ) as client:
            for payload, silent in (
                ({}, False),
                ({"purpose": "login", "silent": True}, True),
                ({"purpose": "link"}, False),
            ):
                response = await client.post("/api/auth/cloud/start/", json=payload)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.json(),
                    {"authorization_url": "https://core.example/authorize"},
                )
                self.assertEqual(handler.execute.await_args.args[0].silent, silent)
            handler.execute.reset_mock()
            response = await client.post(
                "/api/auth/cloud/start/", json={"purpose": "link", "silent": True}
            )
            self.assertEqual(response.status_code, 422)
            handler.execute.assert_not_awaited()

    async def test_application_passes_silent_mode_to_oidc_and_rejects_silent_link(
        self,
    ) -> None:
        context = SimpleNamespace(
            tenant_id=uuid4(), tenant_domain_id=uuid4(), host="tenant.example"
        )
        reader = AsyncMock()
        reader.get_by_host.return_value = context
        connection = SimpleNamespace(
            issuer="https://core.example/issuer", client_id="client"
        )
        connections = AsyncMock()
        connections.connection.return_value = connection
        oidc = AsyncMock()
        oidc.authorization_url.return_value = "https://core.example/authorize"
        handler = StartCloudAuthHandler(
            access=AsyncMock(),
            authentication=AsyncMock(),
            cloud_connection=connections,
            oidc=oidc,
            tenant_reader=reader,
            tokens=TokenManager(InMemoryTokenBackend()),
        )
        await handler.execute(
            StartCloudAuthCommand(
                "tenant.example", None, "browser", "login", silent=True
            )
        )
        self.assertTrue(oidc.authorization_url.await_args.kwargs["silent"])
        oidc.authorization_url.reset_mock()
        with self.assertRaises(IdentityAccessError):
            await handler.execute(
                StartCloudAuthCommand(
                    "tenant.example", None, "browser", "link", silent=True
                )
            )
        oidc.authorization_url.assert_not_awaited()
