from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_EXPORTS: dict[str, str] = {
    "AuthenticatedRequestContextDep": "src.modules.shared.presentation.identity_context",
    "AuthorizationServiceDep": "src.modules.shared.presentation.access",
    "ClockDep": "src.modules.shared.presentation.time",
    "EmailServiceDep": "src.modules.shared.presentation.email",
    "OptionalRequestContextDep": "src.modules.shared.presentation.identity_context",
    "RequestHostDep": "src.modules.shared.presentation.http",
    "TokenManagerDep": "src.modules.shared.presentation.tokens",
    "UoWDep": "src.modules.shared.presentation.persistence",
    "UuidDep": "src.modules.shared.presentation.uuid",
    "build_email_service": "src.modules.shared.presentation.email",
    "default_email_service": "src.modules.shared.presentation.email",
    "default_uuid_generator": "src.modules.shared.presentation.uuid",
    "get_authorization_service": "src.modules.shared.presentation.access",
    "get_clock": "src.modules.shared.presentation.time",
    "get_email_service": "src.modules.shared.presentation.email",
    "get_request_host": "src.modules.shared.presentation.http",
    "get_token_manager": "src.modules.shared.presentation.tokens",
    "get_uow": "src.modules.shared.presentation.persistence",
    "get_uuid_generator": "src.modules.shared.presentation.uuid",
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    """Лениво импортирует presentation wiring export по имени."""

    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}",
        )
    module = import_module(module_path)
    return getattr(module, name)
