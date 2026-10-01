from dataclasses import asdict
from fastapi import APIRouter, Depends, Request
from src.modules.identity.application.invitation.command.revoke_invitation.command import (
    RevokeInvitationCommand,
)
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.invitation.depends import (
    RevokeInvitationHandlerDep,
)
from src.modules.shared.presentation.http.depends import RequestHostDep
from uuid import UUID

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)


@router.delete("/invitations/{invitation_id}")
async def delete_invitation(
    invitation_id: UUID,
    request: Request,
    host: RequestHostDep,
    handler: RevokeInvitationHandlerDep,
):
    return asdict(
        await call(
            handler.execute(
                RevokeInvitationCommand(
                    host=host,
                    session_token=browser_session(request),
                    invitation_id=invitation_id,
                )
            )
        )
    )
