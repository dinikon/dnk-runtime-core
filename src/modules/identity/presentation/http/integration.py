"""Browser identity endpoints; handlers delegate domain decisions to services."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field

from src.config import dnk_config
from src.modules.identity.domain.access import IdentityAccessError
from src.modules.identity.presentation.depends.integration import (
    AccessServiceDep,
    CloudServiceDep,
)
from src.modules.identity.presentation.http.csrf import (
    issue_csrf,
    require_csrf,
    browser_session,
    flow_cookie,
    set_session_cookie,
)
from src.modules.shared.presentation.http.depends import RequestHostDep
from src.modules.shared.infrastructure.observability.metrics import oidc_errors
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)
cloud_router = APIRouter(
    prefix="/api/auth/cloud", tags=["cloud-auth"], dependencies=[Depends(require_csrf)]
)


async def call(operation):
    try:
        return await operation
    except IdentityAccessError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    except TenantHostNotFoundError:
        raise HTTPException(404, "Workspace not found.") from None
    except TenantLoginUnavailableError:
        raise HTTPException(403, "Workspace unavailable.") from None


class InviteRequest(BaseModel):
    email: EmailStr
    role: Literal["admin", "member"] = "member"


class UserAccessRequest(BaseModel):
    role: Literal["admin", "member"] | None = None
    status: Literal["active", "revoked"] | None = None


class InvitationOtpRequest(BaseModel):
    invitation_token: str = Field(min_length=32, max_length=128)


class AcceptInvitationRequest(InvitationOtpRequest):
    token: str = Field(min_length=1, max_length=256)
    code: str = Field(min_length=4, max_length=12)
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)


class CloudStartRequest(BaseModel):
    purpose: Literal["login", "link"] = "login"


@router.get("/auth/csrf")
async def csrf(
    request: Request,
    response: Response,
    tokens: TokenManagerDep,
    host: RequestHostDep,
    service: AccessServiceDep,
):
    await call(service.context(host))
    return await issue_csrf(request, response, tokens)


@router.get("/users")
async def users(request: Request, host: RequestHostDep, service: AccessServiceDep):
    return {"users": await call(service.list_users(host, browser_session(request)))}


@router.patch("/users/{user_id}")
async def update_access(
    user_id: UUID,
    payload: UserAccessRequest,
    request: Request,
    host: RequestHostDep,
    service: AccessServiceDep,
):
    return await call(
        service.change_user(
            host,
            browser_session(request),
            user_id,
            role=payload.role,
            status=payload.status,
        )
    )


@router.get("/invitations")
async def invitations(
    request: Request, host: RequestHostDep, service: AccessServiceDep
):
    return {
        "invitations": await call(
            service.list_invitations(host, browser_session(request))
        )
    }


@router.post("/invitations", status_code=201)
async def create_invitation(
    payload: InviteRequest,
    request: Request,
    host: RequestHostDep,
    service: AccessServiceDep,
):
    return await call(
        service.invite(host, browser_session(request), str(payload.email), payload.role)
    )


@router.delete("/invitations/{invitation_id}")
async def delete_invitation(
    invitation_id: UUID,
    request: Request,
    host: RequestHostDep,
    service: AccessServiceDep,
):
    return await call(
        service.revoke_invitation(host, browser_session(request), invitation_id)
    )


@router.post("/invitations/request-otp")
async def invitation_otp(
    payload: InvitationOtpRequest, host: RequestHostDep, service: AccessServiceDep
):
    result = await call(service.request_invitation_otp(host, payload.invitation_token))
    if dnk_config.DEPLOY_ENV != "DEVELOPMENT":
        result.pop("code", None)
    return result


@router.post("/invitations/accept")
async def accept_invitation(
    payload: AcceptInvitationRequest,
    host: RequestHostDep,
    response: Response,
    service: AccessServiceDep,
):
    context, user, session = await call(
        service.accept_invitation(
            host,
            payload.invitation_token,
            payload.token,
            payload.code,
            payload.first_name.strip(),
            payload.last_name.strip(),
        )
    )
    set_session_cookie(response, session)
    return {"ok": True, "user_id": user.id.uuid, "tenant_id": context.tenant_id}


@cloud_router.get("/status/")
async def cloud_status(
    request: Request, host: RequestHostDep, service: CloudServiceDep
):
    return await call(service.status(host, browser_session(request)))


@cloud_router.post("/start/")
async def cloud_start(
    payload: CloudStartRequest,
    request: Request,
    host: RequestHostDep,
    service: CloudServiceDep,
):
    try:
        return await call(
            service.start(
                host, browser_session(request), flow_cookie(request), payload.purpose
            )
        )
    except HTTPException:
        raise
    except Exception:
        oidc_errors.labels(reason="provider_unavailable").inc()
        # Discovery/transport/library errors never expose provider response bodies.
        raise HTTPException(502, "Cloud identity provider is unavailable.") from None


@cloud_router.get("/callback/")
async def cloud_callback(
    request: Request, host: RequestHostDep, service: CloudServiceDep
):
    query = request.query_params
    try:
        for name in ("state", "code", "iss", "error"):
            if len(query.getlist(name)) > 1:
                raise IdentityAccessError("Duplicate authorization parameter.", 401)
        purpose, session = await service.callback(
            host,
            browser_session(request),
            flow_cookie(request),
            state=query.get("state", ""),
            code=query.get("code", ""),
            issuer=query.get("iss", ""),
            error=query.get("error"),
        )
        response = RedirectResponse(
            "/settings/account" if purpose == "link" else "/", status_code=303
        )
        if session:
            set_session_cookie(response, session)
    except TenantHostNotFoundError:
        await service.local.uow.rollback()
        return JSONResponse({"detail": "Workspace not found."}, status_code=404)
    except Exception:
        await service.local.uow.rollback()
        oidc_errors.labels(reason="callback_invalid").inc()
        response = RedirectResponse(
            "/login?cloud_error=authorization_failed", status_code=303
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@cloud_router.delete("/link/")
async def cloud_unlink(
    request: Request, host: RequestHostDep, service: CloudServiceDep
):
    return await call(service.unlink(host, browser_session(request)))
