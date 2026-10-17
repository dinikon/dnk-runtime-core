from dataclasses import asdict
from fastapi import APIRouter, Depends, Request
from src.modules.identity.application.access.query.list_users.query import (
    ListUsersQuery,
)
from src.modules.identity.presentation.access.depends import ListUsersHandlerDep
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.shared.presentation.http.depends import RequestHostDep

router = APIRouter(
    prefix="/api/console",
    tags=["workspace-access"],
    dependencies=[Depends(require_csrf)],
)


@router.get("/users")
async def users(request: Request, host: RequestHostDep, handler: ListUsersHandlerDep):
    return asdict(
        await call(
            handler.execute(
                ListUsersQuery(host=host, session_token=browser_session(request))
            )
        )
    )
