from __future__ import annotations

from fastapi import APIRouter, Request

from src.modules.identity.application.auth import GetCurrentUserCommandDTO
from src.modules.identity.presentation.depends import (
    AuthSettingsDep,
    GetCurrentUserUseCaseDep,
)
from src.modules.identity.presentation.http.console_auth.controller.error_mapper import (
    raise_get_current_user_http_error,
    to_current_user_response,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    CurrentUserResponseSchema,
)
from src.modules.shared.depends.request_host import RequestHostDep

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
        result = await use_case.execute(
            GetCurrentUserCommandDTO(
                host=host,
                session_token=request.cookies.get(settings.session_cookie_name),
            )
        )
    except Exception as exc:
        raise_get_current_user_http_error(exc)

    return to_current_user_response(result)


__all__ = ["router"]
