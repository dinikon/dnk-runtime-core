from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, Request, status

from src.config import dnk_config
from src.config.auth_config import IdentityAuthSettings
from src.modules.identity.presentation.depends.auth_repositories import (
    AuthUsersRepositoryDep,
    SessionStoreDep,
    TenantContextReaderDep,
)
from src.modules.shared.http.host import extract_request_host
from src.modules.tenancy.domain.errors import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    tenant_id: str | None
    session_id: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...] = ()
    is_authenticated: bool = True


@dataclass(frozen=True, slots=True)
class RequestContext:
    principal: Principal | None
    request_id: str | None
    ip: str | None
    user_agent: str | None


class AuthenticationProcessProtocol(Protocol):
    async def authenticate(self, request: Request) -> Principal | None: ...


class SessionAuthenticationProcess(AuthenticationProcessProtocol):
    def __init__(
        self,
        *,
        settings: IdentityAuthSettings,
        tenant_context_reader: TenantContextReaderDep,
        session_store: SessionStoreDep,
        users_repository: AuthUsersRepositoryDep,
    ) -> None:
        self._settings = settings
        self._tenant_context_reader = tenant_context_reader
        self._session_store = session_store
        self._users_repository = users_repository

    async def authenticate(self, request: Request) -> Principal | None:
        host = extract_request_host(request)
        session_token = request.cookies.get(self._settings.session_cookie_name)

        if not host or not session_token:
            return None

        try:
            tenant_context = await self._tenant_context_reader.get_by_host(host)
        except (TenantHostNotFoundError, TenantLoginUnavailableError):
            return None

        session = await self._session_store.get_session(
            tenant_context.tenant_id,
            session_token,
        )
        if session is None:
            return None
        if (
            session.tenant_id != tenant_context.tenant_id
            or session.tenant_domain_id != tenant_context.tenant_domain_id
            or session.host != tenant_context.host
        ):
            return None

        user = await self._users_repository.get_by_id(session.user_id)
        if user is None or user.tenant_id != tenant_context.tenant_id:
            return None
        if not user.can_login():
            return None

        return Principal(
            user_id=str(user.id),
            tenant_id=str(tenant_context.tenant_id),
            session_id=session.session_id,
            roles=(),
            permissions=(),
            is_authenticated=True,
        )


def get_authentication_settings() -> IdentityAuthSettings:
    return dnk_config.AUTH


AuthenticationSettingsDep = Annotated[
    IdentityAuthSettings,
    Depends(get_authentication_settings),
]


def get_authentication_process(
    request: Request,
    settings: AuthenticationSettingsDep,
    tenant_context_reader: TenantContextReaderDep,
    session_store: SessionStoreDep,
    users_repository: AuthUsersRepositoryDep,
) -> AuthenticationProcessProtocol:
    from_state = getattr(request.app.state, "authentication_process", None)
    if from_state is not None:
        return from_state
    return SessionAuthenticationProcess(
        settings=settings,
        tenant_context_reader=tenant_context_reader,
        session_store=session_store,
        users_repository=users_repository,
    )


AuthenticationProcessDep = Annotated[
    AuthenticationProcessProtocol,
    Depends(get_authentication_process),
]


async def get_authentication_option(
    request: Request,
    authentication_process: AuthenticationProcessDep,
) -> RequestContext:
    principal = await authentication_process.authenticate(request)
    return RequestContext(
        principal=principal,
        request_id=_extract_request_id(request),
        ip=_extract_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


async def get_authentication_strict(
    context: Annotated[RequestContext, Depends(get_authentication_option)],
) -> RequestContext:
    if context.principal is None or not context.principal.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return context


AuthenticationOptionDep = Annotated[
    RequestContext,
    Depends(get_authentication_option),
]
AuthenticationStrictDep = Annotated[
    RequestContext,
    Depends(get_authentication_strict),
]


def _extract_request_id(request: Request) -> str | None:
    request_id = request.headers.get("x-request-id")
    if request_id:
        return request_id
    return request.headers.get("x-correlation-id")


def _extract_request_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip
    client = request.client
    if client is None:
        return None
    return client.host


__all__ = [
    "AuthenticationOptionDep",
    "AuthenticationProcessDep",
    "AuthenticationProcessProtocol",
    "AuthenticationSettingsDep",
    "AuthenticationStrictDep",
    "Principal",
    "RequestContext",
    "SessionAuthenticationProcess",
    "get_authentication_option",
    "get_authentication_process",
    "get_authentication_settings",
    "get_authentication_strict",
]
