from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
)
from src.modules.identity.application.cloud.command.complete_cloud_auth.command import (
    CompleteCloudAuthCommand,
)
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.infrastructure.observability.metrics import oidc_errors
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import flow_cookie
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.csrf import set_session_cookie
from src.modules.identity.presentation.cloud.depends import CompleteCloudAuthHandlerDep
from src.modules.shared.presentation.http.depends import RequestHostDep
from src.modules.shared.presentation.persistence.depends import UoWDep

cloud_router = APIRouter(
    prefix="/api/auth/cloud", tags=["cloud-auth"], dependencies=[Depends(require_csrf)]
)


@cloud_router.get("/callback/")
async def cloud_callback(
    request: Request,
    host: RequestHostDep,
    handler: CompleteCloudAuthHandlerDep,
    uow: UoWDep,
):
    query = request.query_params
    try:
        for name in ("state", "code", "iss", "error"):
            if len(query.getlist(name)) > 1:
                raise IdentityAccessError("Duplicate authorization parameter.", 401)
        result = await handler.execute(
            CompleteCloudAuthCommand(
                host=host,
                session_token=browser_session(request),
                flow_cookie=flow_cookie(request),
                state=query.get("state", ""),
                code=query.get("code", ""),
                issuer=query.get("iss", ""),
                error=query.get("error"),
            )
        )
        response = RedirectResponse(
            "/settings/account" if result.purpose == "link" else "/", status_code=303
        )
        if result.session:
            set_session_cookie(response, result.session)
    except IdentityTenantNotFoundError:
        await uow.rollback()
        return JSONResponse({"detail": "Workspace not found."}, status_code=404)
    except Exception:
        await uow.rollback()
        oidc_errors.labels(reason="callback_invalid").inc()
        response = RedirectResponse(
            "/login?cloud_error=authorization_failed", status_code=303
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
