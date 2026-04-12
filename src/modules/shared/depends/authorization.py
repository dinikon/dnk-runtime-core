from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from src.modules.shared.infrastructure.access import AllowAllAuthorizationService
from src.modules.shared.kernel.access import AuthorizationServiceProtocol

default_authorization_service: AuthorizationServiceProtocol = (
    AllowAllAuthorizationService()
)


def get_authorization_service(request: Request) -> AuthorizationServiceProtocol:
    """Возвращает authorization service из app.state или default allow-all."""

    from_state = getattr(request.app.state, "authorization_service", None)
    if from_state is not None:
        return from_state
    return default_authorization_service


AuthorizationServiceDep = Annotated[
    AuthorizationServiceProtocol,
    Depends(get_authorization_service),
]

__all__ = [
    "AuthorizationServiceDep",
    "default_authorization_service",
    "get_authorization_service",
]
