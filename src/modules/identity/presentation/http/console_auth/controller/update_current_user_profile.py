from __future__ import annotations

from fastapi import APIRouter, Request

from src.modules.identity.application.auth import (
    UpdateCurrentUserProfileCommandDTO,
)
from src.modules.identity.presentation.depends import (
    AuthSettingsDep,
    UpdateCurrentUserProfileUseCaseDep,
)
from src.modules.identity.presentation.http.console_auth.controller.error_mapper import (
    raise_update_current_user_profile_http_error,
    to_current_user_response,
)
from src.modules.identity.presentation.http.console_auth.requests import (
    UpdateCurrentUserProfileRequestSchema,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    CurrentUserResponseSchema,
)
from src.modules.shared.depends.request_host import RequestHostDep

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
    except Exception as exc:
        raise_update_current_user_profile_http_error(exc)

    return to_current_user_response(result)


__all__ = ["router"]
