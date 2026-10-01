from __future__ import annotations
from fastapi import APIRouter, HTTPException, Response, status
from src.modules.identity.application.auth.command.confirm_email_otp.command import (
    ConfirmEmailOtpCommand,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantUnavailableError,
)
from src.modules.identity.domain.auth.error import InvalidOtpChallengeError
from src.modules.identity.domain.auth.error import InvalidOtpCodeError
from src.modules.identity.domain.user.error import PrimaryUserEmailNotFoundError
from src.modules.identity.domain.user.error import UserLoginUnavailableError
from src.modules.identity.presentation.auth.depends import ConfirmEmailOtpHandlerDep
from src.modules.identity.presentation.auth.http.request.confirm_email_otp import (
    ConfirmEmailOtpRequestSchema,
)
from src.modules.identity.presentation.auth.http.response.confirm_email_otp import (
    ConfirmEmailOtpResponseSchema,
)
from src.modules.identity.presentation.auth.providers import AuthSettingsDep
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(tags=["console-auth"])


@router.post("/confirm-otp", response_model=ConfirmEmailOtpResponseSchema)
async def confirm_email_otp(
    payload: ConfirmEmailOtpRequestSchema,
    host: RequestHostDep,
    response: Response,
    settings: AuthSettingsDep,
    use_case: ConfirmEmailOtpHandlerDep,
) -> ConfirmEmailOtpResponseSchema:
    """HTTP endpoint подтверждения OTP и установки session cookie."""
    try:
        result = await use_case.execute(
            ConfirmEmailOtpCommand(
                host=host,
                email=str(payload.email),
                token=payload.token,
                code=payload.code,
            )
        )
    except (IdentityTenantNotFoundError, PrimaryUserEmailNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (IdentityTenantUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
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
        secure=not settings.allow_insecure_http,
        samesite="lax",
        path="/",
    )
    return ConfirmEmailOtpResponseSchema(
        ok=result.ok, user_id=result.user_id, tenant_id=result.tenant_id
    )
