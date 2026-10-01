from dataclasses import asdict
from fastapi import APIRouter, Depends, Request
from src.modules.identity.application.cloud.query.get_cloud_status.query import (
    GetCloudStatusQuery,
)
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.cloud.depends import GetCloudStatusHandlerDep
from src.modules.shared.presentation.http.depends import RequestHostDep

cloud_router = APIRouter(
    prefix="/api/auth/cloud", tags=["cloud-auth"], dependencies=[Depends(require_csrf)]
)


@cloud_router.get("/status/")
async def cloud_status(
    request: Request, host: RequestHostDep, handler: GetCloudStatusHandlerDep
):
    return asdict(
        await call(
            handler.execute(
                GetCloudStatusQuery(host=host, session_token=browser_session(request))
            )
        )
    )
