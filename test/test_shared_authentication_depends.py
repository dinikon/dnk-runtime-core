from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from starlette.requests import Request

from src.config.auth_config import IdentityAuthSettings
from src.modules.identity.application.auth.ports.tenant_context import (
    TenantRequestContext,
)
from src.modules.identity.application.auth.ports.token_store import SessionRecord
from src.modules.shared.depends.authentication import (
    Principal,
    RequestContext,
    SessionAuthenticationProcess,
    get_authentication_option,
    get_authentication_strict,
)


@dataclass(slots=True)
class FakeUser:
    id: UUID
    tenant_id: UUID
    active: bool = True

    def can_login(self) -> bool:
        return self.active


class FakeTenantContextReader:
    def __init__(self, tenant_context: TenantRequestContext):
        self._tenant_context = tenant_context

    async def get_by_host(self, host: str) -> TenantRequestContext:
        return self._tenant_context


class FakeSessionStore:
    def __init__(self, session: SessionRecord | None):
        self._session = session

    async def get_session(
        self,
        tenant_id: UUID,
        token: str,
    ) -> SessionRecord | None:
        return self._session


class FakeUsersRepository:
    def __init__(self, user: FakeUser | None):
        self._user = user

    async def get_by_id(self, user_id: UUID) -> FakeUser | None:
        if self._user is None:
            return None
        if self._user.id != user_id:
            return None
        return self._user


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
    async def test_option_returns_anonymous_context_without_session_cookie(
        self,
    ) -> None:
        process = SessionAuthenticationProcess(
            settings=IdentityAuthSettings(session_cookie_name="dnk_session"),
            tenant_context_reader=FakeTenantContextReader(
                TenantRequestContext(
                    tenant_id=uuid4(),
                    tenant_domain_id=uuid4(),
                    host="acme.local",
                    tenant_status="active",
                    domain_status="active",
                    api_host=None,
                )
            ),
            session_store=FakeSessionStore(None),
            users_repository=FakeUsersRepository(None),
        )
        request = _build_request(
            {
                "host": "acme.local",
                "user-agent": "unit-test",
                "x-request-id": "req-123",
            }
        )

        context = await get_authentication_option(
            request=request,
            authentication_process=process,
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

    async def test_option_returns_principal_for_valid_session(self) -> None:
        tenant_id = uuid4()
        tenant_domain_id = uuid4()
        user_id = uuid4()
        session_id = "session-123"

        process = SessionAuthenticationProcess(
            settings=IdentityAuthSettings(session_cookie_name="dnk_session"),
            tenant_context_reader=FakeTenantContextReader(
                TenantRequestContext(
                    tenant_id=tenant_id,
                    tenant_domain_id=tenant_domain_id,
                    host="acme.local",
                    tenant_status="active",
                    domain_status="active",
                    api_host=None,
                )
            ),
            session_store=FakeSessionStore(
                SessionRecord(
                    token="token-123",
                    session_id=session_id,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    tenant_domain_id=tenant_domain_id,
                    host="acme.local",
                    issued_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC),
                )
            ),
            users_repository=FakeUsersRepository(
                FakeUser(
                    id=user_id,
                    tenant_id=tenant_id,
                    active=True,
                )
            ),
        )
        request = _build_request(
            {
                "host": "acme.local",
                "user-agent": "unit-test",
                "x-forwarded-for": "203.0.113.10, 10.10.10.10",
                "cookie": "dnk_session=token-123",
            }
        )

        context = await get_authentication_option(
            request=request,
            authentication_process=process,
        )

        assert context.principal is not None
        self.assertEqual(
            context.principal,
            Principal(
                user_id=str(user_id),
                tenant_id=str(tenant_id),
                session_id=session_id,
                roles=(),
                permissions=(),
                is_authenticated=True,
            ),
        )
        self.assertEqual(context.request_id, None)
        self.assertEqual(context.ip, "203.0.113.10")
        self.assertEqual(context.user_agent, "unit-test")

    async def test_strict_raises_for_anonymous_context(self) -> None:
        with self.assertRaises(HTTPException) as context_manager:
            await get_authentication_strict(
                RequestContext(
                    principal=None,
                    request_id="req-1",
                    ip="127.0.0.1",
                    user_agent="unit-test",
                )
            )

        self.assertEqual(context_manager.exception.status_code, 401)
        self.assertEqual(context_manager.exception.detail, "Unauthorized.")
