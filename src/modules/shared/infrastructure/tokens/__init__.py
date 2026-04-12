from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_EXPORTS: dict[str, str] = {
    "InMemoryTokenBackend": (
        "src.modules.shared.infrastructure.tokens.in_memory_token_backend"
    ),
    "RedisTokenBackend": "src.modules.shared.infrastructure.tokens.redis_token_backend",
    "RedisTokenRepository": (
        "src.modules.shared.infrastructure.tokens.redis_token_repository"
    ),
}

__all__ = ["InMemoryTokenBackend", "RedisTokenBackend", "RedisTokenRepository"]


def __getattr__(name: str) -> Any:
    """Лениво импортирует token backend/repository по имени export."""

    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}",
        )
    module = import_module(module_path)
    return getattr(module, name)
