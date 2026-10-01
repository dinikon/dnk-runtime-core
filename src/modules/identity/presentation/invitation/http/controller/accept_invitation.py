from fastapi import APIRouter, Depends, Response
from src.modules.identity.application.invitation.command.accept_invitation.command import (
    AcceptInvitationCommand,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.csrf import set_session_cookie
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.invitation.depends import (
    AcceptInvitationHandlerDep,
)
from src.modules.identity.presentation.invitation.http.request import (
    AcceptInvitationRequest,
)
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)


@router.post("/invitations/accept")
async def accept_invitation(
    payload: AcceptInvitationRequest,
    host: RequestHostDep,
    response: Response,
    handler: AcceptInvitationHandlerDep,
):
    result = await call(
        handler.execute(
            AcceptInvitationCommand(
                host=host,
                invitation_token=payload.invitation_token,
                token=payload.token,
                code=payload.code,
                first_name=payload.first_name.strip(),
                last_name=payload.last_name.strip(),
            )
        )
    )
    set_session_cookie(response, result.session)
    return {"ok": True, "user_id": result.user_id, "tenant_id": result.tenant_id}
