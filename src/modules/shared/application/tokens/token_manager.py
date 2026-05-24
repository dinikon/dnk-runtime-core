from __future__ import annotations

from src.modules.shared.application.tokens.token_backend_protocol import (
    TokenBackendProtocol,
)
from src.modules.shared.domain.tokens.stored_token import StoredToken


class TokenManager:
    """Высокоуровневый сервис управления токенами поверх backend-порта."""

    def __init__(self, backend: TokenBackendProtocol):
        """Инициализирует manager backend-реализацией."""
        self._backend = backend

    async def set_token(
        self,
        *,
        prefix: str,
        suffix: str,
        token: str,
        body: dict[str, object],
        ttl: int,
    ) -> None:
        """Сохраняет token body с TTL под составным ключом."""
        await self._backend.set(
            self._build_key(prefix=prefix, suffix=suffix, token=token),
            StoredToken.create(body=body, ttl_seconds=ttl),
        )

    async def exists(self, *, prefix: str, suffix: str, token: str) -> bool:
        """Проверяет наличие неистекшего token."""
        return (
            await self._backend.get(
                self._build_key(prefix=prefix, suffix=suffix, token=token)
            )
            is not None
        )

    async def get_token(
        self,
        *,
        prefix: str,
        suffix: str,
        token: str,
    ) -> dict[str, object] | None:
        """Возвращает token body без удаления token."""
        stored = await self._backend.get(
            self._build_key(prefix=prefix, suffix=suffix, token=token)
        )
        if stored is None:
            return None
        return dict(stored.body)

    async def invalidate(self, *, prefix: str, suffix: str, token: str) -> None:
        """Удаляет token из backend."""
        await self._backend.delete(
            self._build_key(prefix=prefix, suffix=suffix, token=token)
        )

    async def consume_token(
        self,
        *,
        prefix: str,
        suffix: str,
        token: str,
    ) -> dict[str, object] | None:
        """Возвращает token body и сразу удаляет token из backend."""
        key = self._build_key(prefix=prefix, suffix=suffix, token=token)
        stored = await self._backend.get(key)
        if stored is None:
            return None
        await self._backend.delete(key)
        return dict(stored.body)

    @staticmethod
    def _build_key(*, prefix: str, suffix: str, token: str) -> str:
        """Собирает backend key из namespace prefix/suffix и token."""
        return f"{prefix}:{suffix}:{token}"
