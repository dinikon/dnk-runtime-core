from __future__ import annotations

from src.modules.shared.tokens.models import StoredToken


class InMemoryTokenBackend:
    def __init__(self) -> None:
        self._storage: dict[str, StoredToken] = {}

    async def set(self, key: str, value: StoredToken) -> None:
        self._storage[key] = value

    async def get(self, key: str) -> StoredToken | None:
        token = self._storage.get(key)
        if token is None:
            return None
        if token.is_expired():
            self._storage.pop(key, None)
            return None
        return token

    async def delete(self, key: str) -> None:
        self._storage.pop(key, None)

    def clear(self) -> None:
        self._storage.clear()
