from dataclasses import asdict
from fastapi import APIRouter, Depends, Request
from src.modules.identity.application.invitation.query.list_invitations.query import (
    ListInvitationsQuery,
)
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.invitation.depends import (
    ListInvitationsHandlerDep,
)
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)


@router.get("/invitations")
async def invitations(
    request: Request, host: RequestHostDep, handler: ListInvitationsHandlerDep
):
    return asdict(
        await call(
            handler.execute(
                ListInvitationsQuery(host=host, session_token=browser_session(request))
            )
        )
    )
