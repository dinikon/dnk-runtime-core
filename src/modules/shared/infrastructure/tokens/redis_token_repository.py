from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.config import dnk_config

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisTokenRepository:
    def __init__(self, client: "Redis"):
        self._client = client

    @classmethod
    def from_config(cls) -> "RedisTokenRepository":
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
        await self._client.set(name=key, value=json.dumps(payload), ex=ttl)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw_value = await self._client.get(key)
        if raw_value is None:
            return None
        return json.loads(raw_value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

