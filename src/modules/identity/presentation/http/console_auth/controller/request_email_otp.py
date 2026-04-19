from __future__ import annotations

from fastapi import APIRouter

from src.config import dnk_config
from src.modules.identity.application.auth import RequestEmailOtpCommandDTO
from src.modules.identity.presentation.depends import RequestEmailOtpUseCaseDep
from src.modules.identity.presentation.http.console_auth.controller.error_mapper import (
    raise_request_email_otp_http_error,
)
from src.modules.identity.presentation.http.console_auth.requests import (
    RequestEmailOtpRequestSchema,
)
from src.modules.identity.presentation.http.console_auth.responses import (
    RequestEmailOtpResponseSchema,
)
from src.modules.shared.depends.request_host import RequestHostDep

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
        result = await use_case.execute(
            RequestEmailOtpCommandDTO(
                host=host,
                email=str(payload.email),
            )
        )
    except Exception as exc:
        raise_request_email_otp_http_error(exc)

    return RequestEmailOtpResponseSchema(
        token=result.token,
        expires_in=result.expires_in,
        code=result.code if dnk_config.DEPLOY_ENV == "DEVELOPMENT" else None,
    )


__all__ = ["router"]
