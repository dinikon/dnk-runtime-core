from __future__ import annotations

from importlib import import_module
from typing import Any

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

_LAZY_EXPORTS: dict[str, str] = {
    "AuthorizationServiceDep": "src.modules.shared.depends.authorization",
    "ClockDep": "src.modules.shared.depends.clock",
    "EmailServiceDep": "src.modules.shared.depends.email_service",
    "RequestHostDep": "src.modules.shared.depends.request_host",
    "TokenManagerDep": "src.modules.shared.depends.token_manager",
    "UoWDep": "src.modules.shared.depends.uow",
    "get_authorization_service": "src.modules.shared.depends.authorization",
    "get_clock": "src.modules.shared.depends.clock",
    "get_email_service": "src.modules.shared.depends.email_service",
    "get_request_host": "src.modules.shared.depends.request_host",
    "get_token_manager": "src.modules.shared.depends.token_manager",
    "get_uow": "src.modules.shared.depends.uow",
    "default_email_service": "src.modules.shared.depends.email_service",
}
_LAZY_EXPORTS.update(
    {
        export_name: "src.modules.shared.depends.authentication"
        for export_name in _AUTH_EXPORTS
    }
)

__all__ = [
    "AuthorizationServiceDep",
    "ClockDep",
    "EmailServiceDep",
    "RequestHostDep",
    "TokenManagerDep",
    "UoWDep",
    "default_email_service",
    "get_authorization_service",
    "get_clock",
    "get_email_service",
    "get_request_host",
    "get_token_manager",
    "get_uow",
    *_AUTH_EXPORTS,
]


def __getattr__(name: str) -> Any:
    """Лениво импортирует dependency-export по имени из __all__."""

    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}",
        )
    module = import_module(module_path)
    return getattr(module, name)
