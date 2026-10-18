from dataclasses import asdict
from fastapi import APIRouter, Depends, Request
from src.modules.identity.application.cloud.command.unlink_cloud_identity.command import (
    UnlinkCloudIdentityCommand,
)
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.cloud.depends import (
    UnlinkCloudIdentityHandlerDep,
)
from src.modules.shared.presentation.http.depends import RequestHostDep

cloud_router = APIRouter(
    prefix="/api/auth/cloud", tags=["cloud-auth"], dependencies=[Depends(require_csrf)]
)


@cloud_router.delete("/link/")
async def cloud_unlink(
    request: Request, host: RequestHostDep, handler: UnlinkCloudIdentityHandlerDep
):
    return asdict(
        await call(
            handler.execute(
                UnlinkCloudIdentityCommand(
                    host=host, session_token=browser_session(request)
                )
            )
        )
    )
