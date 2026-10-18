from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request, Response, status
from src.modules.identity.application.auth.command.logout_current_session.command import (
    LogoutCurrentSessionCommand,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantUnavailableError,
)
from src.modules.identity.presentation.auth.depends import (
    LogoutCurrentSessionHandlerDep,
)
from src.modules.identity.presentation.auth.http.response.logout_current_session import (
    LogoutCurrentSessionResponseSchema,
)
from src.modules.identity.presentation.auth.providers import AuthSettingsDep
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(tags=["console-auth"])


@router.post("/logout", response_model=LogoutCurrentSessionResponseSchema)
async def logout_current_session(
    request: Request,
    response: Response,
    host: RequestHostDep,
    settings: AuthSettingsDep,
    use_case: LogoutCurrentSessionHandlerDep,
) -> LogoutCurrentSessionResponseSchema:
    """HTTP endpoint logout текущей session и удаления session cookie."""
    try:
        result = await use_case.execute(
            LogoutCurrentSessionCommand(
                host=host,
                session_token=request.cookies.get(settings.session_cookie_name),
            )
        )
    except IdentityTenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except IdentityTenantUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    response.delete_cookie(key=settings.session_cookie_name, path="/", samesite="lax")
    return LogoutCurrentSessionResponseSchema(ok=result.ok)
