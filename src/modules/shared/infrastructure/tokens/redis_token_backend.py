from __future__ import annotations

from src.modules.shared.infrastructure.tokens.redis_token_repository import (
    RedisTokenRepository,
)
from src.modules.shared.kernel.tokens.models import StoredToken


class RedisTokenBackend:
    def __init__(self, repository: RedisTokenRepository):
        self._repository = repository

    @classmethod
    def from_config(cls) -> "RedisTokenBackend":
        return cls(RedisTokenRepository.from_config())

    async def set(self, key: str, value: StoredToken) -> None:
        await self._repository.set_json(
            key=key,
            payload=value.to_dict(),
            ttl=_ttl(value),
        )

    async def get(self, key: str) -> StoredToken | None:
        payload = await self._repository.get_json(key)
        if payload is None:
            return None
        token = StoredToken.from_dict(payload)
        if token.is_expired():
            await self._repository.delete(key)
            return None
        return token

    async def delete(self, key: str) -> None:
        await self._repository.delete(key)


def _ttl(value: StoredToken) -> int:
    from datetime import UTC, datetime

    ttl = int((value.expires_at - datetime.now(UTC)).total_seconds())
    return max(ttl, 1)
