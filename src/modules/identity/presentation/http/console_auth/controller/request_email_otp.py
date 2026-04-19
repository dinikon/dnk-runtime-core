from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.config import dnk_config
from src.modules.identity.application.auth import RequestEmailOtpCommandDTO
from src.modules.identity.domain import (
    PrimaryUserEmailNotFoundError,
    UserLoginUnavailableError,
)
from src.modules.identity.presentation.depends import RequestEmailOtpUseCaseDep
from src.modules.identity.presentation.http.console_auth.requests import (
    RequestEmailOtpRequestSchema,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    RequestEmailOtpResponseSchema,
)
from src.modules.shared.depends.request_host import RequestHostDep
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)

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
