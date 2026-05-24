from __future__ import annotations

from typing import Protocol

from src.modules.shared.domain.tokens.stored_token import StoredToken


class TokenBackendProtocol(Protocol):
    """Порт низкоуровневого хранилища StoredToken."""

    async def set(self, key: str, value: StoredToken) -> None:
        """Сохраняет token по key."""
        ...

    async def get(self, key: str) -> StoredToken | None:
        """Возвращает token по key или None."""
        ...

    async def delete(self, key: str) -> None:
        """Удаляет token по key."""
        ...
