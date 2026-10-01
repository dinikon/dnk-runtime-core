from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.config import dnk_config
from src.modules.identity.application.auth.command.request_email_otp_command_dto import (
    RequestEmailOtpCommandDTO,
)
from src.modules.identity.domain.user.error import PrimaryUserEmailNotFoundError
from src.modules.identity.domain.user.error import UserLoginUnavailableError
from src.modules.identity.presentation.depends.application import (
    RequestEmailOtpUseCaseDep,
)
from src.modules.identity.presentation.http.console_auth.requests.request_email_otp_request import (
    RequestEmailOtpRequestSchema,
)
from src.modules.identity.presentation.http.console_auth.responses.request_email_otp_response import (
    RequestEmailOtpResponseSchema,
)
from src.modules.shared.presentation.http.depends import RequestHostDep
from src.modules.tenancy.domain.tenant_domain.error import TenantHostNotFoundError
from src.modules.tenancy.domain.tenant_domain.error import TenantLoginUnavailableError

router = APIRouter(tags=["console-auth"])


@router.post(
    "/request-otp",
    response_model=RequestEmailOtpResponseSchema,
    response_model_exclude_none=True,
)
async def request_email_otp(
    payload: RequestEmailOtpRequestSchema,
    host: RequestHostDep,
    use_case: RequestEmailOtpUseCaseDep,
) -> RequestEmailOtpResponseSchema:
    """HTTP endpoint запроса email OTP для console login."""
    try:
        result = await use_case(
            RequestEmailOtpCommandDTO(
                host=host,
                email=str(payload.email),
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

    return RequestEmailOtpResponseSchema(
        token=result.token,
        expires_in=result.expires_in,
        code=result.code if dnk_config.DEPLOY_ENV == "DEVELOPMENT" else None,
    )


__all__ = ["router"]
