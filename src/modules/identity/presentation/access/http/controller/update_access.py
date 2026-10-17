from dataclasses import asdict
from fastapi import APIRouter, Depends, Request
from src.modules.identity.application.access.command.change_user_access.command import (
    ChangeUserAccessCommand,
)
from src.modules.identity.presentation.access.depends import ChangeUserAccessHandlerDep
from src.modules.identity.presentation.access.http.request import UserAccessRequest
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.shared.presentation.http.depends import RequestHostDep
from uuid import UUID

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)


@router.patch("/users/{user_id}")
async def update_access(
    user_id: UUID,
    payload: UserAccessRequest,
    request: Request,
    host: RequestHostDep,
    handler: ChangeUserAccessHandlerDep,
):
    return asdict(
        await call(
            handler.execute(
                ChangeUserAccessCommand(
                    host=host,
                    session_token=browser_session(request),
                    user_id=user_id,
                    role=payload.role,
                    status=payload.status,
                )
            )
        )
    )
