from __future__ import annotations

from src.modules.shared.kernel.tokens.models import StoredToken


class InMemoryTokenBackend:
    """In-memory token backend для development/tests fallback."""

    def __init__(self) -> None:
        """Инициализирует пустое локальное token-хранилище."""
        self._storage: dict[str, StoredToken] = {}

    async def set(self, key: str, value: StoredToken) -> None:
        """Сохраняет token по key в памяти процесса."""
        self._storage[key] = value

    async def get(self, key: str) -> StoredToken | None:
        """Возвращает token по key или удаляет истекший token."""
        token = self._storage.get(key)
        if token is None:
            return None
        if token.is_expired():
            self._storage.pop(key, None)
            return None
        return token

    async def delete(self, key: str) -> None:
        """Удаляет token по key, если он существует."""
        self._storage.pop(key, None)

    def clear(self) -> None:
        """Полностью очищает in-memory token storage."""
        self._storage.clear()
