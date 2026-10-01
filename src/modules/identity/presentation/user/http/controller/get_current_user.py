from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request, status
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantUnavailableError,
)
from src.modules.identity.application.user.query.get_current_user.dto import (
    GetCurrentUserResultDTO,
)
from src.modules.identity.application.user.query.get_current_user.query import (
    GetCurrentUserQuery,
)
from src.modules.identity.domain.auth.error import InvalidSessionError
from src.modules.identity.domain.user.error import UserLoginUnavailableError
from src.modules.identity.presentation.auth.providers import AuthSettingsDep
from src.modules.identity.presentation.user.depends import GetCurrentUserHandlerDep
from src.modules.identity.presentation.user.http.response.current_user import (
    CurrentUserResponseSchema,
)
from src.modules.identity.presentation.user.http.response.current_user_email import (
    CurrentUserEmailResponseSchema,
)
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(tags=["console-auth"])


@router.get("/me", response_model=CurrentUserResponseSchema)
async def get_current_user(
    request: Request,
    host: RequestHostDep,
    settings: AuthSettingsDep,
    use_case: GetCurrentUserHandlerDep,
) -> CurrentUserResponseSchema:
    """HTTP endpoint получения профиля текущего пользователя."""
    try:
        result = await use_case.execute(
            GetCurrentUserQuery(
                host=host,
                session_token=request.cookies.get(settings.session_cookie_name),
            )
        )
    except IdentityTenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (IdentityTenantUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except InvalidSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    return _to_current_user_response(result)


def _to_current_user_response(
    result: GetCurrentUserResultDTO,
) -> CurrentUserResponseSchema:
    """Мапит DTO текущего пользователя в HTTP response schema."""
    return CurrentUserResponseSchema(
        id=result.id,
        status=result.status,
        role=result.role,
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
