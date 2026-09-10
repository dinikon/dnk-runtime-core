from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.identity.application.auth import ConfirmEmailOtpCommandDTO
from src.modules.identity.domain import (
    InvalidOtpChallengeError,
    InvalidOtpCodeError,
    PrimaryUserEmailNotFoundError,
    UserLoginUnavailableError,
)
from src.modules.identity.presentation.depends import (
    AuthSettingsDep,
    ConfirmEmailOtpUseCaseDep,
)
from src.modules.identity.presentation.http.console_auth.requests import (
    ConfirmEmailOtpRequestSchema,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    ConfirmEmailOtpResponseSchema,
)
from src.modules.shared.presentation.http.depends import RequestHostDep
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)

router = APIRouter(tags=["console-auth"])


@router.post(
    "/confirm-otp",
    response_model=ConfirmEmailOtpResponseSchema,
)
async def confirm_email_otp(
    payload: ConfirmEmailOtpRequestSchema,
    host: RequestHostDep,
    response: Response,
    settings: AuthSettingsDep,
    use_case: ConfirmEmailOtpUseCaseDep,
) -> ConfirmEmailOtpResponseSchema:
    """HTTP endpoint подтверждения OTP и установки session cookie."""
    try:
        result = await use_case(
            ConfirmEmailOtpCommandDTO(
                host=host,
                email=str(payload.email),
                token=payload.token,
                code=payload.code,
            )
        )
    except (TenantHostNotFoundError, PrimaryUserEmailNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (TenantLoginUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (InvalidOtpChallengeError, InvalidOtpCodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
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


__all__ = ["router"]
