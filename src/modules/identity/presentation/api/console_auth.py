from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from src.config import dnk_config
from src.modules.identity.application.auth.dto import (
    ConfirmEmailOtpCommandDTO,
    GetCurrentUserCommandDTO,
    GetCurrentUserEmailDTO,
    GetCurrentUserResultDTO,
    LogoutCurrentSessionCommandDTO,
    RequestEmailOtpCommandDTO,
    UpdateCurrentUserProfileCommandDTO,
    UpdateCurrentUserProfileResultDTO,
)
from src.modules.identity.domain.errors import (
    InvalidSessionError,
    InvalidOtpChallengeError,
    InvalidOtpCodeError,
    PrimaryUserEmailNotFoundError,
    UserLoginUnavailableError,
)
from src.modules.identity.presentation.api.requests.console_auth import (
    ConfirmEmailOtpRequestSchema,
    RequestEmailOtpRequestSchema,
    UpdateCurrentUserProfileRequestSchema,
)
from src.modules.identity.presentation.api.responses.console_auth import (
    ConfirmEmailOtpResponseSchema,
    CurrentUserEmailResponseSchema,
    CurrentUserResponseSchema,
    LogoutCurrentSessionResponseSchema,
    RequestEmailOtpResponseSchema,
)
from src.modules.identity.presentation.depends.auth_services import AuthSettingsDep
from src.modules.identity.presentation.depends.auth_use_cases import (
    ConfirmEmailOtpUseCaseDep,
    GetCurrentUserUseCaseDep,
    LogoutCurrentSessionUseCaseDep,
    RequestEmailOtpUseCaseDep,
    UpdateCurrentUserProfileUseCaseDep,
)
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.depends.request_host import RequestHostDep
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)

router = APIRouter(tags=["console-auth"])


def _map_current_user_emails(
    emails: list[GetCurrentUserEmailDTO],
) -> list[CurrentUserEmailResponseSchema]:
    """Мапит email DTO текущего пользователя в response schemas."""

    return [
        CurrentUserEmailResponseSchema(
            id=email.id,
            email=email.email,
            is_primary=email.is_primary,
            is_verified=email.is_verified,
        )
        for email in emails
    ]


def _to_current_user_response(
    result: GetCurrentUserResultDTO | UpdateCurrentUserProfileResultDTO,
) -> CurrentUserResponseSchema:
    """Мапит DTO профиля текущего пользователя в HTTP response schema."""
    return CurrentUserResponseSchema(
        id=result.id,
        status=result.status,
        last_name=result.last_name,
        first_name=result.first_name,
        middle_name=result.middle_name,
        avatar=result.avatar,
        interface_language=result.interface_language,
        interface_theme=result.interface_theme,
        timezone=result.timezone,
        emails=_map_current_user_emails(result.emails),
    )


def _is_dev_mode() -> bool:
    """Проверяет, что приложение запущено в development окружении."""
    return dnk_config.DEPLOY_ENV == "DEVELOPMENT"


@router.post(
    "/request-otp",
    response_model=RequestEmailOtpResponseSchema,
    response_model_exclude_none=True,
)
async def request_email_otp(
    payload: RequestEmailOtpRequestSchema,
    host: RequestHostDep,
    use_case: RequestEmailOtpUseCaseDep,
) -> RequestEmailOtpResponseSchema:
    """HTTP endpoint запроса email OTP для console login."""
    try:
        result = await use_case.execute(
            RequestEmailOtpCommandDTO(
                host=host,
                email=str(payload.email),
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (TenantLoginUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except PrimaryUserEmailNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return RequestEmailOtpResponseSchema(
        token=result.token,
        expires_in=result.expires_in,
        code=result.code if _is_dev_mode() else None,
    )


@router.post(
    "/confirm-otp",
    response_model=ConfirmEmailOtpResponseSchema,
)
async def confirm_email_otp(
    payload: ConfirmEmailOtpRequestSchema,
    host: RequestHostDep,
    response: Response,
    settings: AuthSettingsDep,
    use_case: ConfirmEmailOtpUseCaseDep,
) -> ConfirmEmailOtpResponseSchema:
    """HTTP endpoint подтверждения OTP и установки session cookie."""
    try:
        result = await use_case.execute(
            ConfirmEmailOtpCommandDTO(
                host=host,
                email=str(payload.email),
                token=payload.token,
                code=payload.code,
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (TenantLoginUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except PrimaryUserEmailNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (InvalidOtpChallengeError, InvalidOtpCodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.session_token,
        max_age=result.expires_in,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return ConfirmEmailOtpResponseSchema(
        ok=result.ok,
        user_id=result.user_id,
        tenant_id=result.tenant_id,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponseSchema,
)
async def get_current_user(
    request: Request,
    host: RequestHostDep,
    settings: AuthSettingsDep,
    use_case: GetCurrentUserUseCaseDep,
) -> CurrentUserResponseSchema:
    """HTTP endpoint получения профиля текущего пользователя."""
    try:
        result = await use_case.execute(
            GetCurrentUserCommandDTO(
                host=host,
                session_token=request.cookies.get(settings.session_cookie_name),
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (TenantLoginUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except InvalidSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return _to_current_user_response(result)


@router.patch(
    "/me",
    response_model=CurrentUserResponseSchema,
)
async def update_current_user_profile(
    payload: UpdateCurrentUserProfileRequestSchema,
    request: Request,
    host: RequestHostDep,
    settings: AuthSettingsDep,
    use_case: UpdateCurrentUserProfileUseCaseDep,
) -> CurrentUserResponseSchema:
    """HTTP endpoint обновления профиля текущего пользователя."""
    try:
        result = await use_case.execute(
            UpdateCurrentUserProfileCommandDTO(
                host=host,
                session_token=request.cookies.get(settings.session_cookie_name),
                last_name=payload.last_name,
                first_name=payload.first_name,
                middle_name=payload.middle_name,
                interface_language=payload.interface_language,
                interface_theme=payload.interface_theme,
                timezone=payload.timezone,
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (TenantLoginUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except InvalidSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _to_current_user_response(result)


@router.post(
    "/logout",
    response_model=LogoutCurrentSessionResponseSchema,
)
async def logout_current_session(
    request: Request,
    response: Response,
    host: RequestHostDep,
    settings: AuthSettingsDep,
    use_case: LogoutCurrentSessionUseCaseDep,
) -> LogoutCurrentSessionResponseSchema:
    """HTTP endpoint logout текущей session и удаления session cookie."""
    try:
        result = await use_case.execute(
            LogoutCurrentSessionCommandDTO(
                host=host,
                session_token=request.cookies.get(settings.session_cookie_name),
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TenantLoginUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        samesite="lax",
    )
    return LogoutCurrentSessionResponseSchema(ok=result.ok)


__all__ = ["router"]
