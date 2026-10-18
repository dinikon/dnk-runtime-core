from dataclasses import asdict
from fastapi import APIRouter, Depends, Request
from src.modules.identity.application.invitation.command.create_invitation.command import (
    CreateInvitationCommand,
)
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.invitation.depends import (
    CreateInvitationHandlerDep,
)
from src.modules.identity.presentation.invitation.http.request import InviteRequest
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)


@router.post("/invitations", status_code=201)
async def create_invitation(
    payload: InviteRequest,
    request: Request,
    host: RequestHostDep,
    handler: CreateInvitationHandlerDep,
):
    return asdict(
        await call(
            handler.execute(
                CreateInvitationCommand(
                    host=host,
                    session_token=browser_session(request),
                    email=str(payload.email),
                    role=payload.role,
                )
            )
        )
    )
