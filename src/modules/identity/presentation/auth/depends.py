from __future__ import annotations
from fastapi import Depends
from fastapi import Depends, HTTPException, Request, status
from src.config import dnk_config
from src.modules.identity.application.auth.command.confirm_email_otp.handler import (
    ConfirmEmailOtpHandler,
)
from src.modules.identity.application.auth.command.logout_current_session.handler import (
    LogoutCurrentSessionHandler,
)
from src.modules.identity.application.auth.command.request_email_otp.handler import (
    RequestEmailOtpHandler,
)
from src.modules.identity.application.auth.query.authenticate_by_session.handler import (
    AuthenticateBySessionHandler,
)
from src.modules.identity.application.auth.query.authenticate_by_session.query import (
    AuthenticateBySessionQuery,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.providers import AuthSettingsDep
from src.modules.identity.presentation.auth.providers import OtpChallengeStoreDep
from src.modules.identity.presentation.auth.providers import OtpServiceDep
from src.modules.identity.presentation.auth.providers import SessionServiceDep
from src.modules.identity.presentation.auth.providers import SessionStoreDep
from src.modules.identity.presentation.auth.providers import TenantContextReaderDep
from src.modules.identity.presentation.email.depends import EmailServiceDep
from src.modules.identity.presentation.user.providers import UsersRepositoryDep
from src.modules.shared.presentation.http.host import extract_request_host
from src.modules.shared.presentation.persistence.depends import UoWDep
from typing import Annotated


def get_request_email_otp_handler(
    tenant_context_reader: TenantContextReaderDep,
    users_repository: UsersRepositoryDep,
    otp_challenge_store: OtpChallengeStoreDep,
    otp_service: OtpServiceDep,
    email_service: EmailServiceDep,
    settings: AuthSettingsDep,
) -> RequestEmailOtpHandler:
    """Создает use case запроса email OTP."""
    return RequestEmailOtpHandler(
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        otp_challenge_store=otp_challenge_store,
        otp_service=otp_service,
        email_service=email_service,
        otp_ttl_seconds=settings.otp_token_ttl_seconds,
    )


RequestEmailOtpHandlerDep = Annotated[
    RequestEmailOtpHandler, Depends(get_request_email_otp_handler)
]


def get_authenticate_by_session_handler(
    tenant_context_reader: TenantContextReaderDep,
    users_repository: UsersRepositoryDep,
    session_store: SessionStoreDep,
) -> AuthenticateBySessionHandler:
    """Создает use case аутентификации по session."""
    return AuthenticateBySessionHandler(
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        session_store=session_store,
    )


AuthenticateBySessionHandlerDep = Annotated[
    AuthenticateBySessionHandler, Depends(get_authenticate_by_session_handler)
]


def get_confirm_email_otp_handler(
    uow: UoWDep,
    tenant_context_reader: TenantContextReaderDep,
    users_repository: UsersRepositoryDep,
    otp_challenge_store: OtpChallengeStoreDep,
    session_store: SessionStoreDep,
    otp_service: OtpServiceDep,
    session_service: SessionServiceDep,
    settings: AuthSettingsDep,
) -> ConfirmEmailOtpHandler:
    """Создает use case подтверждения email OTP."""
    return ConfirmEmailOtpHandler(
        uow=uow,
        tenant_context_reader=tenant_context_reader,
        users_repository=users_repository,
        otp_challenge_store=otp_challenge_store,
        session_store=session_store,
        otp_service=otp_service,
        session_service=session_service,
        session_ttl_seconds=settings.session_ttl_seconds,
    )


ConfirmEmailOtpHandlerDep = Annotated[
    ConfirmEmailOtpHandler, Depends(get_confirm_email_otp_handler)
]


def get_logout_current_session_handler(
    tenant_context_reader: TenantContextReaderDep, session_store: SessionStoreDep
) -> LogoutCurrentSessionHandler:
    """Создает use case logout текущей session."""
    return LogoutCurrentSessionHandler(
        tenant_context_reader=tenant_context_reader, session_store=session_store
    )


LogoutCurrentSessionHandlerDep = Annotated[
    LogoutCurrentSessionHandler, Depends(get_logout_current_session_handler)
]


async def get_optional_request_context(
    request: Request, handler: AuthenticateBySessionHandlerDep
) -> RequestContext:
    """Строит RequestContext с optional principal из session cookie."""
    auth_settings = dnk_config.AUTH
    query = AuthenticateBySessionQuery(
        host=extract_request_host(request),
        session_token=request.cookies.get(auth_settings.session_cookie_name),
    )
    result = await handler.execute(query)
    principal = (
        None
        if result is None
        else Principal(
            user_id=result.user_id,
            tenant_id=result.tenant_id,
            session_id=result.session_id,
            roles=result.roles,
            permissions=result.permissions,
            is_authenticated=result.is_authenticated,
        )
    )
    return RequestContext(
        principal=principal,
        request_id=_extract_request_id(request),
        ip=_extract_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


async def require_authenticated_request_context(
    context: Annotated[RequestContext, Depends(get_optional_request_context)],
) -> RequestContext:
    """Возвращает context только для аутентифицированного principal."""
    if context.principal is None or not context.principal.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized."
        )
    return context


OptionalRequestContextDep = Annotated[
    RequestContext, Depends(get_optional_request_context)
]
AuthenticatedRequestContextDep = Annotated[
    RequestContext, Depends(require_authenticated_request_context)
]


def _extract_request_id(request: Request) -> str | None:
    """Достает request/correlation id из HTTP headers."""
    request_id = request.headers.get("x-request-id")
    if request_id:
        return request_id
    return request.headers.get("x-correlation-id")


def _extract_request_ip(request: Request) -> str | None:
    """Reads the client address normalized by the trusted ingress boundary."""
    client = request.client
    if client is None:
        return None
    return client.host
