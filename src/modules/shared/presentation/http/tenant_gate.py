"""Hold tenant admission through the complete ASGI request and response."""

from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.routing import Match
from sqlalchemy import select

from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.persistence.tenant_gate import (
    TenantGate,
    TenantUnavailable,
)
from src.modules.shared.presentation.http.host import extract_request_host
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


class TenantAdmissionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"} or scope.get(
            "path", ""
        ).startswith(("/internal/", "/health/")):
            return await self.app(scope, receive, send)
        request = HTTPConnection(scope)
        # An unmatched route only returns a technical 404/405 and has no tenant
        # handler to protect (also keeps such responses independent of the DB).
        if not any(
            route.matches(scope)[0] == Match.FULL for route in request.app.router.routes
        ):
            return await self.app(scope, receive, send)
        sessions = getattr(request.app.state, "db", db_helper.session_factory)
        async with sessions() as session:
            tenant_id = await session.scalar(
                select(TenantDomainModel.tenant_id).where(
                    TenantDomainModel.host == extract_request_host(request)
                )
            )
        if tenant_id is None:
            return await self.app(scope, receive, send)
        try:
            async with TenantGate(sessions).hold(tenant_id) as connection:
                request.state.tenant_connection = connection
                await self.app(scope, receive, send)
        except TenantUnavailable:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                await JSONResponse(
                    {"detail": "Workspace unavailable.", "code": "tenant_unavailable"},
                    status_code=403,
                    headers={"Cache-Control": "no-store"},
                )(scope, receive, send)
