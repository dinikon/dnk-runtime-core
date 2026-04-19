from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException, status

from src.modules.identity.application.auth import (
    GetCurrentUserEmailDTO,
    GetCurrentUserResultDTO,
    UpdateCurrentUserProfileResultDTO,
)
from src.modules.identity.domain import (
    InvalidOtpChallengeError,
    InvalidOtpCodeError,
    InvalidSessionError,
    PrimaryUserEmailNotFoundError,
    UserLoginUnavailableError,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    CurrentUserEmailResponseSchema,
    CurrentUserResponseSchema,
)
from src.modules.shared.domain.errors import DomainError
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)


def to_current_user_response(
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


def raise_request_email_otp_http_error(exc: Exception) -> NoReturn:
    """Мапит ошибки request OTP в HTTPException."""
    if isinstance(exc, (TenantHostNotFoundError, PrimaryUserEmailNotFoundError)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, (TenantLoginUnavailableError, UserLoginUnavailableError)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    raise exc


def raise_confirm_email_otp_http_error(exc: Exception) -> NoReturn:
    """Мапит ошибки confirm OTP в HTTPException."""
    if isinstance(exc, (TenantHostNotFoundError, PrimaryUserEmailNotFoundError)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, (TenantLoginUnavailableError, UserLoginUnavailableError)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    if isinstance(exc, (InvalidOtpChallengeError, InvalidOtpCodeError)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    raise exc


def raise_get_current_user_http_error(exc: Exception) -> NoReturn:
    """Мапит ошибки get current user в HTTPException."""
    if isinstance(exc, TenantHostNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, (TenantLoginUnavailableError, UserLoginUnavailableError)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    if isinstance(exc, InvalidSessionError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    raise exc


def raise_update_current_user_profile_http_error(exc: Exception) -> NoReturn:
    """Мапит ошибки update current user profile в HTTPException."""
    if isinstance(exc, TenantHostNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, (TenantLoginUnavailableError, UserLoginUnavailableError)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    if isinstance(exc, InvalidSessionError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    if isinstance(exc, DomainError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    raise exc


def raise_logout_current_session_http_error(exc: Exception) -> NoReturn:
    """Мапит ошибки logout current session в HTTPException."""
    if isinstance(exc, TenantHostNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, TenantLoginUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    raise exc


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


__all__ = [
    "raise_confirm_email_otp_http_error",
    "raise_get_current_user_http_error",
    "raise_logout_current_session_http_error",
    "raise_request_email_otp_http_error",
    "raise_update_current_user_profile_http_error",
    "to_current_user_response",
]
