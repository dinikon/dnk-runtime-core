from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from src.modules.identity.application.auth import (
    GetCurrentUserCommandDTO,
    GetCurrentUserResultDTO,
)
from src.modules.identity.domain import InvalidSessionError, UserLoginUnavailableError
from src.modules.identity.presentation.depends import (
    AuthSettingsDep,
    GetCurrentUserUseCaseDep,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    CurrentUserEmailResponseSchema,
    CurrentUserResponseSchema,
)
from src.modules.shared.presentation.http.depends import RequestHostDep
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)

router = APIRouter(tags=["console-auth"])


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
        result = await use_case(
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


def _to_current_user_response(
    result: GetCurrentUserResultDTO,
) -> CurrentUserResponseSchema:
    """Мапит DTO текущего пользователя в HTTP response schema."""
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
