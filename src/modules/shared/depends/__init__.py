from __future__ import annotations

from importlib import import_module
from typing import Any

from src.modules.shared.depends.request_host import RequestHostDep, get_request_host
from src.modules.shared.depends.uow import UoWDep, get_uow

_AUTH_EXPORTS = {
    "AuthenticatedRequestContextDep",
    "AuthenticateBySessionCommand",
    "AuthenticationProcessDep",
    "AuthenticationProcessProtocol",
    "AuthenticateBySessionUseCaseAdapter",
    "OptionalRequestContextDep",
    "Principal",
    "RequestContext",
    "get_authentication_process",
    "get_optional_request_context",
    "require_authenticated_request_context",
}

__all__ = [
    "RequestHostDep",
    "UoWDep",
    "get_request_host",
    "get_uow",
    *_AUTH_EXPORTS,
]


def __getattr__(name: str) -> Any:
    if name not in _AUTH_EXPORTS:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}",
        )
    auth_module = import_module("src.modules.shared.depends.authentication")
    return getattr(auth_module, name)
