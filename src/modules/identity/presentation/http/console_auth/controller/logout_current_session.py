from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from src.modules.identity.application.auth import LogoutCurrentSessionCommandDTO
from src.modules.identity.presentation.depends import (
    AuthSettingsDep,
    LogoutCurrentSessionUseCaseDep,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    LogoutCurrentSessionResponseSchema,
)
from src.modules.shared.depends.request_host import RequestHostDep
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)

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
        result = await use_case(
            LogoutCurrentSessionCommandDTO(
                host=host,
                session_token=request.cookies.get(settings.session_cookie_name),
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except TenantLoginUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        samesite="lax",
    )
    return LogoutCurrentSessionResponseSchema(ok=result.ok)


__all__ = ["router"]
