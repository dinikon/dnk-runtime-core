from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, Request

from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.infrastructure.tokens import (
    InMemoryTokenBackend,
    RedisTokenBackend,
)

log = logging.getLogger(__name__)


def _build_default_token_manager() -> TokenManager:
    """Создает Redis-backed TokenManager или in-memory fallback."""

    try:
        return TokenManager(RedisTokenBackend.from_config())
    except RuntimeError as exc:
        log.warning(
            "Redis token backend is unavailable, using in-memory fallback: %s",
            exc,
        )
        return TokenManager(InMemoryTokenBackend())


default_token_manager = _build_default_token_manager()


def get_token_manager(request: Request) -> TokenManager:
    """Возвращает token manager из app.state или default singleton."""
    from_state = getattr(request.app.state, "token_manager", None)
    if from_state is not None:
        return from_state
    return default_token_manager


TokenManagerDep = Annotated[TokenManager, Depends(get_token_manager)]

__all__ = ["TokenManagerDep", "default_token_manager", "get_token_manager"]
