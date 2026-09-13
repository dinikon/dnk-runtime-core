import asyncio
import os
import unittest
from uuid import uuid4

from redis.asyncio import Redis
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.infrastructure.tokens.redis_token_backend import (
    RedisTokenBackend,
)
from src.modules.shared.infrastructure.tokens.redis_token_repository import (
    RedisTokenRepository,
)


@unittest.skipUnless(
    os.environ.get("TEST_REDIS_URL"), "Set TEST_REDIS_URL to disposable Redis."
)
class RedisAtomicStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_separate_clients_consume_once(self):
        clients = [
            Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
            for _ in range(8)
        ]
        managers = [
            TokenManager(RedisTokenBackend(RedisTokenRepository(c))) for c in clients
        ]
        namespace = str(uuid4())
        try:
            await managers[0].set_token(
                prefix="test_state",
                suffix=namespace,
                token="one",
                body={"nonce": "once"},
                ttl=30,
            )
            replies = await asyncio.gather(
                *[
                    m.consume_token(prefix="test_state", suffix=namespace, token="one")
                    for m in managers
                ]
            )
            self.assertEqual(sum(r is not None for r in replies), 1)
        finally:
            for client in clients:
                await client.aclose()
