from __future__ import annotations
from fastapi import APIRouter, HTTPException, status
from src.config import dnk_config
from src.modules.identity.application.auth.command.request_email_otp.command import (
    RequestEmailOtpCommand,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantUnavailableError,
)
from src.modules.identity.domain.user.error import PrimaryUserEmailNotFoundError
from src.modules.identity.domain.user.error import UserLoginUnavailableError
from src.modules.identity.presentation.auth.depends import RequestEmailOtpHandlerDep
from src.modules.identity.presentation.auth.http.request.request_email_otp import (
    RequestEmailOtpRequestSchema,
)
from src.modules.identity.presentation.auth.http.response.request_email_otp import (
    RequestEmailOtpResponseSchema,
)
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(tags=["console-auth"])


@router.post(
    "/request-otp",
    response_model=RequestEmailOtpResponseSchema,
    response_model_exclude_none=True,
)
async def request_email_otp(
    payload: RequestEmailOtpRequestSchema,
    host: RequestHostDep,
    use_case: RequestEmailOtpHandlerDep,
) -> RequestEmailOtpResponseSchema:
    """HTTP endpoint запроса email OTP для console login."""
    try:
        result = await use_case.execute(
            RequestEmailOtpCommand(host=host, email=str(payload.email))
        )
    except (IdentityTenantNotFoundError, PrimaryUserEmailNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (IdentityTenantUnavailableError, UserLoginUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    return RequestEmailOtpResponseSchema(
        token=result.token,
        expires_in=result.expires_in,
        code=result.code if dnk_config.DEPLOY_ENV == "DEVELOPMENT" else None,
    )
