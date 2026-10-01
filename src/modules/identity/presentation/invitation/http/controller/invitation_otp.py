from dataclasses import asdict
from fastapi import APIRouter, Depends
from src.config import dnk_config
from src.modules.identity.application.invitation.command.request_invitation_otp.command import (
    RequestInvitationOtpCommand,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.invitation.depends import (
    RequestInvitationOtpHandlerDep,
)
from src.modules.identity.presentation.invitation.http.request import (
    InvitationOtpRequest,
)
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)


@router.post("/invitations/request-otp")
async def invitation_otp(
    payload: InvitationOtpRequest,
    host: RequestHostDep,
    handler: RequestInvitationOtpHandlerDep,
):
    result = asdict(
        await call(
            handler.execute(
                RequestInvitationOtpCommand(
                    host=host, invitation_token=payload.invitation_token
                )
            )
        )
    )
    if dnk_config.DEPLOY_ENV != "DEVELOPMENT":
        result.pop("code", None)
    return result
