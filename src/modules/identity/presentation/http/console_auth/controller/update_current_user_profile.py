from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from src.modules.identity.application.auth import (
    UpdateCurrentUserProfileCommandDTO,
    UpdateCurrentUserProfileResultDTO,
)
from src.modules.identity.domain import InvalidSessionError, UserLoginUnavailableError
from src.modules.identity.presentation.depends import (
    AuthSettingsDep,
    UpdateCurrentUserProfileUseCaseDep,
)
from src.modules.identity.presentation.http.console_auth.requests import (
    UpdateCurrentUserProfileRequestSchema,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    CurrentUserEmailResponseSchema,
    CurrentUserResponseSchema,
)
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.depends.request_host import RequestHostDep
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)

router = APIRouter(tags=["console-auth"])


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
        result = await use_case(
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return _to_current_user_response(result)


def _to_current_user_response(
    result: UpdateCurrentUserProfileResultDTO,
) -> CurrentUserResponseSchema:
    """Мапит DTO обновленного профиля в HTTP response schema."""
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
        emails=[
            CurrentUserEmailResponseSchema(
                id=email.id,
                email=email.email,
                is_primary=email.is_primary,
                is_verified=email.is_verified,
            )
            for email in result.emails
        ],
    )


__all__ = ["router"]
