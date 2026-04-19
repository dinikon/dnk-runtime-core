from __future__ import annotations

import unittest
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.config.feature.identity.auth_config import IdentityAuthSettings
from src.modules.identity.application.auth import (
    ConfirmEmailOtpResultDTO,
    LogoutCurrentSessionResultDTO,
)
from src.modules.identity.domain.auth import InvalidOtpCodeError, InvalidSessionError
from src.modules.identity.presentation.depends.application import (
    get_current_user_use_case,
    get_confirm_email_otp_use_case,
    get_logout_current_session_use_case,
    get_request_email_otp_use_case,
    get_update_current_user_profile_use_case,
)
from src.modules.identity.presentation.depends.infrastructure import get_auth_settings
from src.modules.identity.presentation.http.router import router
from src.modules.shared.depends.request_host import get_request_host
from src.modules.shared.domain.errors import DomainError
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)


class _ConfirmEmailOtpUseCaseStub:

    async def __call__(self, dto) -> ConfirmEmailOtpResultDTO:
        return ConfirmEmailOtpResultDTO(
            ok=True,
            user_id=uuid4(),
            tenant_id=uuid4(),
            session_token="sess_token",
            expires_in=3600,
        )


class _LogoutCurrentSessionUseCaseStub:

    async def __call__(self, dto) -> LogoutCurrentSessionResultDTO:
        return LogoutCurrentSessionResultDTO(ok=True)


class _UpdateCurrentUserProfileUseCaseStub:

    async def __call__(self, dto):
        raise DomainError("Profile payload is invalid.")


class _RequestEmailOtpNotFoundUseCaseStub:

    async def __call__(self, dto):
        raise TenantHostNotFoundError("tenant.example.com")


class _RequestEmailOtpForbiddenUseCaseStub:

    async def __call__(self, dto):
        raise TenantLoginUnavailableError("tenant.example.com")


class _ConfirmEmailOtpUnauthorizedUseCaseStub:
    async def __call__(self, dto):
        raise InvalidOtpCodeError()


class _GetCurrentUserUnauthorizedUseCaseStub:
    async def __call__(self, dto):
        raise InvalidSessionError()


class IdentityHttpRouterTests(unittest.TestCase):
    def test_router_keeps_public_identity_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/request-otp"), routes)
        self.assertIn(("POST", "/confirm-otp"), routes)
        self.assertIn(("GET", "/me"), routes)
        self.assertIn(("PATCH", "/me"), routes)
        self.assertIn(("POST", "/logout"), routes)

    def test_confirm_email_otp_sets_session_cookie(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console/auth")
        app.dependency_overrides[get_confirm_email_otp_use_case] = (
            lambda: _ConfirmEmailOtpUseCaseStub()
        )
        app.dependency_overrides[get_auth_settings] = lambda: IdentityAuthSettings(
            session_cookie_name="dnk_session"
        )
        app.dependency_overrides[get_request_host] = lambda: "tenant.example.com"

        response = TestClient(app).post(
            "/api/console/auth/confirm-otp",
            json={
                "email": "john@example.com",
                "token": "otp_token",
                "code": "123456",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("dnk_session=sess_token", response.headers["set-cookie"])

    def test_logout_deletes_session_cookie(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console/auth")
        app.dependency_overrides[get_logout_current_session_use_case] = (
            lambda: _LogoutCurrentSessionUseCaseStub()
        )
        app.dependency_overrides[get_auth_settings] = lambda: IdentityAuthSettings(
            session_cookie_name="dnk_session"
        )
        app.dependency_overrides[get_request_host] = lambda: "tenant.example.com"

        client = TestClient(app)
        client.cookies.set("dnk_session", "sess_token")
        response = client.post("/api/console/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertIn("dnk_session=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_update_profile_maps_domain_error_to_422(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console/auth")
        app.dependency_overrides[get_update_current_user_profile_use_case] = (
            lambda: _UpdateCurrentUserProfileUseCaseStub()
        )
        app.dependency_overrides[get_auth_settings] = lambda: IdentityAuthSettings(
            session_cookie_name="dnk_session"
        )
        app.dependency_overrides[get_request_host] = lambda: "tenant.example.com"

        client = TestClient(app)
        client.cookies.set("dnk_session", "sess_token")
        response = client.patch(
            "/api/console/auth/me",
            json={
                "last_name": "Doe",
                "first_name": "John",
                "middle_name": None,
                "interface_language": "uk",
                "interface_theme": "system",
                "timezone": "Europe/Kyiv",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Profile payload is invalid.")

    def test_request_otp_maps_tenant_host_not_found_to_404(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console/auth")
        app.dependency_overrides[get_request_email_otp_use_case] = (
            lambda: _RequestEmailOtpNotFoundUseCaseStub()
        )
        app.dependency_overrides[get_request_host] = lambda: "tenant.example.com"

        response = TestClient(app).post(
            "/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Tenant for host 'tenant.example.com' was not found.",
        )

    def test_request_otp_maps_tenant_login_unavailable_to_403(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console/auth")
        app.dependency_overrides[get_request_email_otp_use_case] = (
            lambda: _RequestEmailOtpForbiddenUseCaseStub()
        )
        app.dependency_overrides[get_request_host] = lambda: "tenant.example.com"

        response = TestClient(app).post(
            "/api/console/auth/request-otp",
            json={"email": "john@example.com"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Tenant for host 'tenant.example.com' is not available for login.",
        )

    def test_confirm_otp_maps_invalid_code_to_401(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console/auth")
        app.dependency_overrides[get_confirm_email_otp_use_case] = (
            lambda: _ConfirmEmailOtpUnauthorizedUseCaseStub()
        )
        app.dependency_overrides[get_request_host] = lambda: "tenant.example.com"

        response = TestClient(app).post(
            "/api/console/auth/confirm-otp",
            json={
                "email": "john@example.com",
                "token": "otp_token",
                "code": "123456",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "OTP code is invalid.")

    def test_get_current_user_maps_invalid_session_to_401(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/console/auth")
        app.dependency_overrides[get_current_user_use_case] = (
            lambda: _GetCurrentUserUnauthorizedUseCaseStub()
        )
        app.dependency_overrides[get_auth_settings] = lambda: IdentityAuthSettings(
            session_cookie_name="dnk_session"
        )
        app.dependency_overrides[get_request_host] = lambda: "tenant.example.com"

        client = TestClient(app)
        client.cookies.set("dnk_session", "sess_token")
        response = client.get("/api/console/auth/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Session is invalid or expired.")


__all__ = ["IdentityHttpRouterTests"]
