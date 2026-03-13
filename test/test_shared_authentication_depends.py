from __future__ import annotations

import unittest

from fastapi import HTTPException
from starlette.requests import Request

from src.modules.shared.depends.authentication import (
    AuthenticateBySessionCommand,
    AuthenticationProcessProtocol,
    get_optional_request_context,
    require_authenticated_request_context,
)
from src.modules.shared.kernel.principal import Principal
from src.modules.shared.kernel.request_context import RequestContext


class FakeAuthenticationProcess(AuthenticationProcessProtocol):
    def __init__(self, principal: Principal | None):
        self._principal = principal
        self.last_command: AuthenticateBySessionCommand | None = None

    async def authenticate(
        self,
        command: AuthenticateBySessionCommand,
    ) -> Principal | None:
        self.last_command = command
        return self._principal


def _build_request(headers: dict[str, str]) -> Request:
    encoded_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in headers.items()
    ]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": encoded_headers,
        "client": ("10.10.10.10", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class TestSharedAuthenticationDepends(unittest.IsolatedAsyncioTestCase):

    async def test_option_builds_command_and_returns_anonymous_context(self) -> None:
        process = FakeAuthenticationProcess(principal=None)
        request = _build_request(
            {
                "host": "acme.local",
                "user-agent": "unit-test",
                "x-request-id": "req-123",
            }
        )

        context = await get_optional_request_context(
            request=request,
            authentication_process=process,
        )

        self.assertEqual(
            process.last_command,
            AuthenticateBySessionCommand(
                host="acme.local",
                session_token=None,
                ip="10.10.10.10",
                user_agent="unit-test",
            ),
        )
        self.assertEqual(
            context,
            RequestContext(
                principal=None,
                request_id="req-123",
                ip="10.10.10.10",
                user_agent="unit-test",
            ),
        )

    async def test_option_uses_process_result_principal(self) -> None:
        principal = Principal(
            user_id="user-1",
            tenant_id="tenant-1",
            session_id="session-1",
            roles=("admin",),
            permissions=("crm.read",),
            is_authenticated=True,
        )
        process = FakeAuthenticationProcess(principal=principal)
        request = _build_request(
            {
                "host": "acme.local",
                "user-agent": "unit-test",
                "x-forwarded-for": "203.0.113.10, 10.10.10.10",
                "cookie": "dnk_session=token-123",
            }
        )

        context = await get_optional_request_context(
            request=request,
            authentication_process=process,
        )

        self.assertEqual(
            process.last_command,
            AuthenticateBySessionCommand(
                host="acme.local",
                session_token="token-123",
                ip="203.0.113.10",
                user_agent="unit-test",
            ),
        )
        self.assertEqual(context.principal, principal)
        self.assertEqual(context.request_id, None)
        self.assertEqual(context.ip, "203.0.113.10")
        self.assertEqual(context.user_agent, "unit-test")

    async def test_strict_raises_for_anonymous_context(self) -> None:
        with self.assertRaises(HTTPException) as context_manager:
            await require_authenticated_request_context(
                RequestContext(
                    principal=None,
                    request_id="req-1",
                    ip="127.0.0.1",
                    user_agent="unit-test",
                )
            )

        self.assertEqual(context_manager.exception.status_code, 401)
        self.assertEqual(context_manager.exception.detail, "Unauthorized.")
