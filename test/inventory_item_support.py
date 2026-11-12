"""HTTP-сборка InventoryItem с настоящими authentication и CSRF dependencies."""

from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from src.config import dnk_config
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.inventory.presentation.inventory_item.router import router
from src.modules.inventory.presentation.uom.router import router as uoms_router
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


def inventory_item_app(
    sessions: Any, context: RequestContext, *, scoped_connection: bool = False
) -> FastAPI:
    """Собирает изолированное приложение с опциональным tenant-соединением."""
    app = FastAPI()
    app.state.db = sessions
    app.state.test_context = context
    app.state.token_manager = TokenManager(InMemoryTokenBackend())
    app.include_router(router, prefix="/api/console")
    app.include_router(uoms_router, prefix="/api/console")
    app.dependency_overrides[get_optional_request_context] = (
        lambda: app.state.test_context
    )

    if scoped_connection:

        class TestTenantConnection:
            """Привязывает схему тестового principal до открытия общего UoW."""

            def __init__(self, wrapped: ASGIApp) -> None:
                """Сохраняет обёрнутое ASGI-приложение."""
                self.wrapped = wrapped

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                """Открывает отдельное соединение на каждый tenant-запрос."""
                principal = app.state.test_context.principal
                if (
                    scope["type"] != "http"
                    or principal is None
                    or not principal.tenant_id
                ):
                    await self.wrapped(scope, receive, send)
                    return
                naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
                async with sessions.kw["bind"].connect() as connection:
                    await bind_tenant_schema(
                        connection, UUID(principal.tenant_id), naming
                    )
                    scope.setdefault("state", {})["tenant_connection"] = connection
                    await self.wrapped(scope, receive, send)

        app.add_middleware(TestTenantConnection)

    @app.get("/csrf")
    async def csrf(
        request: Request, response: Response, tokens: TokenManagerDep
    ) -> dict[str, str]:
        """Выдаёт настоящий CSRF-токен для тестовых POST-запросов."""
        return await issue_csrf(request, response, tokens)

    return app
