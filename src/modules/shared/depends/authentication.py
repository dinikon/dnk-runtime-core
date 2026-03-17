from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, Request, status

from src.config import dnk_config
from src.modules.identity.application.auth.use_cases.authenticate_by_session import (
    AuthenticateBySessionCommand as AuthenticateBySessionUseCaseCommand,
    SessionPrincipal,
)
from src.modules.identity.presentation.depends.auth_use_cases import (
    AuthenticateBySessionUseCaseDep,
)
from src.modules.shared.http.host import extract_request_host
from src.modules.shared.kernel.principal import Principal
from src.modules.shared.kernel.request_context import RequestContext


@dataclass(frozen=True, slots=True)
class AuthenticateBySessionCommand:
    host: str | None
    session_token: str | None
    ip: str | None
    user_agent: str | None


class AuthenticationProcessProtocol(Protocol):

    async def authenticate(
        self,
        command: AuthenticateBySessionCommand,
    ) -> Principal | None: ...


class AuthenticateBySessionUseCaseAdapter(AuthenticationProcessProtocol):
    def __init__(self, use_case: AuthenticateBySessionUseCaseDep) -> None:
        self._use_case = use_case

    async def authenticate(
        self,
        command: AuthenticateBySessionCommand,
    ) -> Principal | None:
        principal = await self._use_case.execute(
            AuthenticateBySessionUseCaseCommand(
                host=command.host,
                session_token=command.session_token,
                ip=command.ip,
                user_agent=command.user_agent,
            )
        )
        if principal is None:
            return None
        return _map_principal(principal)


def get_authentication_process(
    request: Request,
    use_case: AuthenticateBySessionUseCaseDep,
) -> AuthenticationProcessProtocol:
    from_state = getattr(request.app.state, "authentication_process", None)
    if from_state is not None:
        return from_state
    return AuthenticateBySessionUseCaseAdapter(use_case)


AuthenticationProcessDep = Annotated[
    AuthenticationProcessProtocol,
    Depends(get_authentication_process),
]


async def get_optional_request_context(
    request: Request,
    authentication_process: AuthenticationProcessDep,
) -> RequestContext:
    auth_settings = dnk_config.AUTH
    command = AuthenticateBySessionCommand(
        host=extract_request_host(request),
        session_token=request.cookies.get(auth_settings.session_cookie_name),
        ip=_extract_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    principal = await authentication_process.authenticate(command)
    return RequestContext(
        principal=principal,
        request_id=_extract_request_id(request),
        ip=command.ip,
        user_agent=command.user_agent,
    )


async def require_authenticated_request_context(
    context: Annotated[RequestContext, Depends(get_optional_request_context)],
) -> RequestContext:
    if context.principal is None or not context.principal.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return context


OptionalRequestContextDep = Annotated[
    RequestContext,
    Depends(get_optional_request_context),
]
AuthenticatedRequestContextDep = Annotated[
    RequestContext,
    Depends(require_authenticated_request_context),
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


def _map_principal(principal: SessionPrincipal) -> Principal:
    return Principal(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        session_id=principal.session_id,
        roles=principal.roles,
        permissions=principal.permissions,
        is_authenticated=principal.is_authenticated,
    )


__all__ = [
    "AuthenticatedRequestContextDep",
    "AuthenticateBySessionCommand",
    "AuthenticationProcessDep",
    "AuthenticationProcessProtocol",
    "AuthenticateBySessionUseCaseAdapter",
    "OptionalRequestContextDep",
    "Principal",
    "RequestContext",
    "get_authentication_process",
    "get_optional_request_context",
    "require_authenticated_request_context",
]
