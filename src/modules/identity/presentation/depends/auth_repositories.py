from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from src.modules.identity.application.auth.ports.repositories import (
    AuthUserRepositoryPort,
)
from src.modules.identity.application.auth.ports.tenant_context import (
    TenantContextReaderPort,
    TenantRequestContext,
)
from src.modules.identity.application.auth.ports.token_store import (
    OtpChallenge,
    OtpChallengeStorePort,
    SessionRecord,
    SessionStorePort,
)
from src.modules.identity.presentation.depends.repositories import UsersRepositoryDep
from src.modules.shared.kernel.tokens import TokenManager
from src.modules.tenancy.application.queries import (
    ResolveTenantRequestContextByHostQuery,
)
from src.modules.tenancy.presentation.depends.application import (
    TenantRequestContextByHostUseCaseDep,
)

from src.modules.shared.depends.token_manager import TokenManagerDep


class TenancyTenantContextReaderAdapter(TenantContextReaderPort):
    def __init__(self, use_case: TenantRequestContextByHostUseCaseDep):
        self._use_case = use_case

    async def get_by_host(self, host: str) -> TenantRequestContext:
        result = await self._use_case.execute(
            ResolveTenantRequestContextByHostQuery(host=host)
        )
        return TenantRequestContext(
            tenant_id=result.tenant_id,
            tenant_domain_id=result.tenant_domain_id,
            host=result.host,
            tenant_status=result.tenant_status,
            domain_status=result.domain_status,
            api_host=result.api_host,
        )


class TokenManagerBackedOtpChallengeStore(OtpChallengeStorePort):
    def __init__(self, token_manager: TokenManager):
        self._token_manager = token_manager

    async def create_challenge(self, challenge: OtpChallenge, ttl_seconds: int) -> None:
        await self._token_manager.set_token(
            prefix="otp_login",
            suffix=str(challenge.tenant_id),
            token=challenge.token,
            body={
                "token": challenge.token,
                "email": challenge.email,
                "tenant_id": challenge.tenant_id,
                "tenant_domain_id": challenge.tenant_domain_id,
                "host": challenge.host,
                "code_hash": challenge.code_hash,
                "created_at": challenge.created_at,
            },
            ttl=ttl_seconds,
        )

    async def get_challenge(self, tenant_id: UUID, token: str) -> OtpChallenge | None:
        body = await self._token_manager.get_token(
            prefix="otp_login",
            suffix=str(tenant_id),
            token=token,
        )
        if body is None:
            return None
        return OtpChallenge(
            token=_required_str(body, "token"),
            email=_required_str(body, "email"),
            tenant_id=_required_uuid(body, "tenant_id"),
            tenant_domain_id=_required_uuid(body, "tenant_domain_id"),
            host=_required_str(body, "host"),
            code_hash=_required_str(body, "code_hash"),
            created_at=_required_datetime(body, "created_at"),
        )

    async def invalidate_challenge(self, tenant_id: UUID, token: str) -> None:
        await self._token_manager.invalidate(
            prefix="otp_login",
            suffix=str(tenant_id),
            token=token,
        )


class TokenManagerBackedSessionStore(SessionStorePort):
    def __init__(self, token_manager: TokenManager):
        self._token_manager = token_manager

    async def create_session(self, session: SessionRecord, ttl_seconds: int) -> None:
        await self._token_manager.set_token(
            prefix="session",
            suffix=str(session.tenant_id),
            token=session.token,
            body={
                "token": session.token,
                "session_id": session.session_id,
                "user_id": session.user_id,
                "tenant_id": session.tenant_id,
                "tenant_domain_id": session.tenant_domain_id,
                "host": session.host,
                "issued_at": session.issued_at,
                "expires_at": session.expires_at,
            },
            ttl=ttl_seconds,
        )

    async def get_session(self, tenant_id: UUID, token: str) -> SessionRecord | None:
        body = await self._token_manager.get_token(
            prefix="session",
            suffix=str(tenant_id),
            token=token,
        )
        if body is None:
            return None
        return SessionRecord(
            token=_required_str(body, "token"),
            session_id=_required_str(body, "session_id"),
            user_id=_required_uuid(body, "user_id"),
            tenant_id=_required_uuid(body, "tenant_id"),
            tenant_domain_id=_required_uuid(body, "tenant_domain_id"),
            host=_required_str(body, "host"),
            issued_at=_required_datetime(body, "issued_at"),
            expires_at=_required_datetime(body, "expires_at"),
        )

    async def invalidate_session(self, tenant_id: UUID, token: str) -> None:
        await self._token_manager.invalidate(
            prefix="session",
            suffix=str(tenant_id),
            token=token,
        )


def get_auth_users_repository(
    users_repository: UsersRepositoryDep,
) -> AuthUserRepositoryPort:
    return users_repository


AuthUsersRepositoryDep = Annotated[
    AuthUserRepositoryPort,
    Depends(get_auth_users_repository),
]


def get_tenant_context_reader(
    use_case: TenantRequestContextByHostUseCaseDep,
) -> TenantContextReaderPort:
    return TenancyTenantContextReaderAdapter(use_case)


TenantContextReaderDep = Annotated[
    TenantContextReaderPort,
    Depends(get_tenant_context_reader),
]


def get_otp_challenge_store(
    token_manager: TokenManagerDep,
) -> OtpChallengeStorePort:
    return TokenManagerBackedOtpChallengeStore(token_manager)


OtpChallengeStoreDep = Annotated[
    OtpChallengeStorePort,
    Depends(get_otp_challenge_store),
]


def get_session_store(token_manager: TokenManagerDep) -> SessionStorePort:
    return TokenManagerBackedSessionStore(token_manager)


SessionStoreDep = Annotated[SessionStorePort, Depends(get_session_store)]


def _required_str(body: dict[str, object], key: str) -> str:
    value = body[key]
    assert isinstance(value, str)
    return value


def _required_uuid(body: dict[str, object], key: str) -> UUID:
    value = body[key]
    if isinstance(value, UUID):
        return value
    assert isinstance(value, str)
    return UUID(value)


def _required_datetime(body: dict[str, object], key: str) -> datetime:
    value = body[key]
    assert isinstance(value, datetime)
    return value


__all__ = [
    "AuthUsersRepositoryDep",
    "OtpChallengeStoreDep",
    "SessionStoreDep",
    "TenantContextReaderDep",
    "TenancyTenantContextReaderAdapter",
    "TokenManagerBackedOtpChallengeStore",
    "TokenManagerBackedSessionStore",
    "get_auth_users_repository",
    "get_otp_challenge_store",
    "get_session_store",
    "get_tenant_context_reader",
]
