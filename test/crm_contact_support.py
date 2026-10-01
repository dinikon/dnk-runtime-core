"""Изолированная HTTP-сборка CRM с настоящими authentication/CSRF dependencies."""

from fastapi import FastAPI, Request, Response

from src.modules.crm.presentation.contact.http.router import router
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.shared.presentation.tokens.depends import TokenManagerDep


def contact_app(sessions, context):
    app = FastAPI()
    app.state.db = sessions
    app.state.test_context = context
    app.state.token_manager = TokenManager(InMemoryTokenBackend())
    app.include_router(router, prefix="/api/console")
    app.dependency_overrides[get_optional_request_context] = (
        lambda: app.state.test_context
    )

    @app.get("/csrf")
    async def csrf(request: Request, response: Response, tokens: TokenManagerDep):
        return await issue_csrf(request, response, tokens)

    return app
