from fastapi import HTTPException, Request
from src.modules.identity.application.cloud.command.start_cloud_auth.command import (
    StartCloudAuthCommand,
)
from src.modules.identity.infrastructure.observability.metrics import oidc_errors
from src.modules.identity.presentation.auth.http.csrf import browser_session
from src.modules.identity.presentation.auth.http.csrf import flow_cookie
from src.modules.identity.presentation.auth.http.errors import call
from src.modules.identity.presentation.cloud.depends import StartCloudAuthHandlerDep
from src.modules.identity.presentation.cloud.http.request.cloud_start import (
    CloudStartRequest,
)
from src.modules.identity.presentation.cloud.http.response.cloud_start import (
    CloudStartResponse,
)
from src.modules.shared.presentation.http.depends import RequestHostDep


async def cloud_start(
    payload: CloudStartRequest,
    request: Request,
    host: RequestHostDep,
    handler: StartCloudAuthHandlerDep,
) -> CloudStartResponse:
    """Запускает облачный вход и возвращает URL без выдачи credentials браузеру."""
    try:
        result = await call(
            handler.execute(
                StartCloudAuthCommand(
                    host=host,
                    session_token=browser_session(request),
                    flow_cookie=flow_cookie(request),
                    purpose=payload.purpose,
                    silent=payload.silent,
                )
            )
        )
        return CloudStartResponse(authorization_url=result.authorization_url)
    except HTTPException:
        raise
    except Exception:
        oidc_errors.labels(reason="provider_unavailable").inc()
        raise HTTPException(502, "Cloud identity provider is unavailable.") from None
