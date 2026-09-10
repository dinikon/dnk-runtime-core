from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from src.config import dnk_config
from src.modules.identity.presentation.depends import AuthenticateBySessionUseCaseDep
from src.modules.shared.domain.identity_context import RequestContext
from src.modules.shared.presentation.http.host import extract_request_host
from src.modules.shared.presentation.identity_context.authenticate_by_session_command import (
    AuthenticateBySessionCommand,
)
from src.modules.shared.presentation.identity_context.authenticate_by_session_use_case_adapter import (
    AuthenticateBySessionUseCaseAdapter,
)
from src.modules.shared.presentation.identity_context.authentication_process_protocol import (
    AuthenticationProcessProtocol,
)


def get_authentication_process(
    request: Request,
    use_case: AuthenticateBySessionUseCaseDep,
) -> AuthenticationProcessProtocol:
    """Возвращает authentication process из app.state или default adapter."""
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
    """Строит RequestContext с optional principal из session cookie."""
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
    """Возвращает context только для аутентифицированного principal."""
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
    """Достает request/correlation id из HTTP headers."""
    request_id = request.headers.get("x-request-id")
    if request_id:
        return request_id
    return request.headers.get("x-correlation-id")


def _extract_request_ip(request: Request) -> str | None:
    """Достает client ip из x-forwarded-for или request.client."""
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
    "AuthenticatedRequestContextDep",
    "AuthenticateBySessionCommand",
    "AuthenticationProcessDep",
    "AuthenticationProcessProtocol",
    "AuthenticateBySessionUseCaseAdapter",
    "OptionalRequestContextDep",
    "RequestContext",
    "get_authentication_process",
    "get_optional_request_context",
    "require_authenticated_request_context",
]
