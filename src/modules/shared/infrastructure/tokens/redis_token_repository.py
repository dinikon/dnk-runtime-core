from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.config import dnk_config

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisTokenRepository:
    """Низкоуровневый JSON repository для token payloads в Redis."""

    def __init__(self, client: "Redis"):
        """Инициализирует repository готовым Redis client."""
        self._client = client

    @classmethod
    def from_config(cls) -> "RedisTokenRepository":
        """Создает Redis client из конфигурации приложения."""
        try:
            from redis.asyncio import Redis
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Redis dependency is not installed. Add the 'redis' package to the environment."
            ) from exc

        client = Redis(
            host=dnk_config.REDIS_HOST,
            port=dnk_config.REDIS_PORT,
            username=dnk_config.REDIS_USERNAME or None,
            password=dnk_config.REDIS_PASSWORD or None,
            ssl=dnk_config.REDIS_USE_SSL,
            db=dnk_config.REDIS_DB,
            decode_responses=True,
        )
        return cls(client)

    async def set_json(self, key: str, payload: dict[str, object], ttl: int) -> None:
        """Сохраняет JSON payload по key с TTL."""
        await self._client.set(name=key, value=json.dumps(payload), ex=ttl)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Читает JSON payload по key или возвращает None."""
        raw_value = await self._client.get(key)
        if raw_value is None:
            return None
        return json.loads(raw_value)

    async def delete(self, key: str) -> None:
        """Удаляет payload из Redis по key."""
        await self._client.delete(key)
