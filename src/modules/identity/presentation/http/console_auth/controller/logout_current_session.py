from __future__ import annotations

from fastapi import APIRouter, Request, Response

from src.modules.identity.application.auth import LogoutCurrentSessionCommandDTO
from src.modules.identity.presentation.depends import (
    AuthSettingsDep,
    LogoutCurrentSessionUseCaseDep,
)
from src.modules.identity.presentation.http.console_auth.controller.error_mapper import (
    raise_logout_current_session_http_error,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    LogoutCurrentSessionResponseSchema,
)
from src.modules.shared.depends.request_host import RequestHostDep

router = APIRouter(tags=["console-auth"])


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
    except Exception as exc:
        raise_logout_current_session_http_error(exc)

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        samesite="lax",
    )
    return LogoutCurrentSessionResponseSchema(ok=result.ok)


__all__ = ["router"]
