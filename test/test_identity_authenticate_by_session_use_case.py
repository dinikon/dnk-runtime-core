from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.identity.application.auth.ports.tenant_context import (
    TenantRequestContext,
)
from src.modules.identity.application.auth.ports.token_store import SessionRecord
from src.modules.identity.application.auth.use_cases.authenticate_by_session import (
    AuthenticateBySessionCommand,
    AuthenticateBySessionUseCase,
    SessionPrincipal,
)
from src.modules.tenancy.domain.errors import TenantHostNotFoundError


@dataclass(slots=True)
class FakeUser:
    id: UUID
    tenant_id: UUID
    active: bool = True

    def can_login(self) -> bool:
        return self.active


class FakeTenantContextReader:
    def __init__(
        self,
        tenant_context: TenantRequestContext | None = None,
        raise_not_found: bool = False,
    ):
        self._tenant_context = tenant_context
        self._raise_not_found = raise_not_found

    async def get_by_host(self, host: str) -> TenantRequestContext:
        if self._raise_not_found:
            raise TenantHostNotFoundError(host)
        assert self._tenant_context is not None
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


class TestAuthenticateBySessionUseCase(unittest.IsolatedAsyncioTestCase):
    async def test_execute_returns_none_without_host_or_token(self) -> None:
        tenant_id = uuid4()
        use_case = AuthenticateBySessionUseCase(
            tenant_context_reader=FakeTenantContextReader(
                tenant_context=TenantRequestContext(
                    tenant_id=tenant_id,
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

        result = await use_case.execute(
            AuthenticateBySessionCommand(
                host=None,
                session_token=None,
                ip=None,
                user_agent=None,
            )
        )

        self.assertIsNone(result)

    async def test_execute_returns_principal_for_valid_session(self) -> None:
        tenant_id = uuid4()
        tenant_domain_id = uuid4()
        user_id = uuid4()
        session_id = "session-123"

        use_case = AuthenticateBySessionUseCase(
            tenant_context_reader=FakeTenantContextReader(
                tenant_context=TenantRequestContext(
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
                )
            ),
        )

        result = await use_case.execute(
            AuthenticateBySessionCommand(
                host="acme.local",
                session_token="token-123",
                ip="203.0.113.10",
                user_agent="unit-test",
            )
        )

        self.assertEqual(
            result,
            SessionPrincipal(
                user_id=str(user_id),
                tenant_id=str(tenant_id),
                session_id=session_id,
                roles=(),
                permissions=(),
                is_authenticated=True,
            ),
        )

    async def test_execute_returns_none_for_missing_tenant_context(self) -> None:
        use_case = AuthenticateBySessionUseCase(
            tenant_context_reader=FakeTenantContextReader(raise_not_found=True),
            session_store=FakeSessionStore(None),
            users_repository=FakeUsersRepository(None),
        )

        result = await use_case.execute(
            AuthenticateBySessionCommand(
                host="unknown.local",
                session_token="token-123",
                ip=None,
                user_agent=None,
            )
        )

        self.assertIsNone(result)

    async def test_execute_returns_none_for_inactive_user(self) -> None:
        tenant_id = uuid4()
        tenant_domain_id = uuid4()
        user_id = uuid4()

        use_case = AuthenticateBySessionUseCase(
            tenant_context_reader=FakeTenantContextReader(
                tenant_context=TenantRequestContext(
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
                    session_id="session-123",
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
                    active=False,
                )
            ),
        )

        result = await use_case.execute(
            AuthenticateBySessionCommand(
                host="acme.local",
                session_token="token-123",
                ip=None,
                user_agent=None,
            )
        )

        self.assertIsNone(result)
