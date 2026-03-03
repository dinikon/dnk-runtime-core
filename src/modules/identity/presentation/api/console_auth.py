from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from src.modules.identity.application.auth.dto import (
    ConfirmEmailOtpCommandDTO,
    LogoutCurrentSessionCommandDTO,
    RequestEmailOtpCommandDTO,
)
from src.modules.identity.domain.errors import (
    InvalidOtpChallengeError,
    InvalidOtpCodeError,
    PrimaryUserEmailNotFoundError,
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
    UserLoginUnavailableError,
)
from src.modules.identity.presentation.depends.auth_services import AuthSettingsDep
from src.modules.identity.presentation.depends.auth_use_cases import (
    ConfirmEmailOtpUseCaseDep,
    LogoutCurrentSessionUseCaseDep,
    RequestEmailOtpUseCaseDep,
)

router = APIRouter(tags=["console-auth"])


class RequestEmailOtpRequestSchema(BaseModel):
    email: EmailStr


class RequestEmailOtpResponseSchema(BaseModel):
    token: str
    expires_in: int


class ConfirmEmailOtpRequestSchema(BaseModel):
    email: EmailStr
    token: str
    code: str


class ConfirmEmailOtpResponseSchema(BaseModel):
    ok: bool
    user_id: UUID
    tenant_id: UUID


class LogoutCurrentSessionResponseSchema(BaseModel):
    ok: bool


@router.post(
    "/api/console/auth/request-otp",
    response_model=RequestEmailOtpResponseSchema,
)
async def request_email_otp(
    payload: RequestEmailOtpRequestSchema,
    request: Request,
    use_case: RequestEmailOtpUseCaseDep,
) -> RequestEmailOtpResponseSchema:
    try:
        result = await use_case.execute(
            RequestEmailOtpCommandDTO(
                host=_get_request_host(request),
                email=str(payload.email),
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (TenantLoginUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except PrimaryUserEmailNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return RequestEmailOtpResponseSchema(
        token=result.token,
        expires_in=result.expires_in,
    )


@router.post(
    "/api/console/auth/confirm-otp",
    response_model=ConfirmEmailOtpResponseSchema,
)
async def confirm_email_otp(
    payload: ConfirmEmailOtpRequestSchema,
    request: Request,
    response: Response,
    settings: AuthSettingsDep,
    use_case: ConfirmEmailOtpUseCaseDep,
) -> ConfirmEmailOtpResponseSchema:
    try:
        result = await use_case.execute(
            ConfirmEmailOtpCommandDTO(
                host=_get_request_host(request),
                email=str(payload.email),
                token=payload.token,
                code=payload.code,
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (TenantLoginUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except PrimaryUserEmailNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (InvalidOtpChallengeError, InvalidOtpCodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.session_token,
        max_age=result.expires_in,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return ConfirmEmailOtpResponseSchema(
        ok=result.ok,
        user_id=result.user_id,
        tenant_id=result.tenant_id,
    )


@router.post(
    "/api/console/auth/logout",
    response_model=LogoutCurrentSessionResponseSchema,
)
async def logout_current_session(
    request: Request,
    response: Response,
    settings: AuthSettingsDep,
    use_case: LogoutCurrentSessionUseCaseDep,
) -> LogoutCurrentSessionResponseSchema:
    try:
        result = await use_case.execute(
            LogoutCurrentSessionCommandDTO(
                host=_get_request_host(request),
                session_token=request.cookies.get(settings.session_cookie_name),
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TenantLoginUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        samesite="lax",
    )
    return LogoutCurrentSessionResponseSchema(ok=result.ok)


def _get_request_host(request: Request) -> str:
    return request.url.hostname or request.headers.get("host", "")


__all__ = ["router"]
