"""Изолированная HTTP-сборка CRM с настоящими authentication/CSRF dependencies."""

from uuid import UUID

from fastapi import FastAPI, Request, Response

from src.config import dnk_config
from src.modules.crm.presentation.contact.http.router import router
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


def contact_app(sessions, context, *, scoped_connection=False):
    app = FastAPI()
    app.state.db = sessions
    app.state.test_context = context
    app.state.token_manager = TokenManager(InMemoryTokenBackend())
    app.include_router(router, prefix="/api/console")
    app.dependency_overrides[get_optional_request_context] = (
        lambda: app.state.test_context
    )

    if scoped_connection:

        class TestTenantConnection:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            async def __call__(self, scope, receive, send):
                principal = app.state.test_context.principal
                if (
                    scope["type"] != "http"
                    or principal is None
                    or not principal.tenant_id
                ):
                    return await self.wrapped(scope, receive, send)
                naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
                async with sessions.kw["bind"].connect() as connection:
                    await bind_tenant_schema(
                        connection, UUID(principal.tenant_id), naming
                    )
                    scope.setdefault("state", {})["tenant_connection"] = connection
                    await self.wrapped(scope, receive, send)

        app.add_middleware(TestTenantConnection)

    @app.get("/csrf")
    async def csrf(request: Request, response: Response, tokens: TokenManagerDep):
        return await issue_csrf(request, response, tokens)

    return app
