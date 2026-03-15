from __future__ import annotations

import unittest

from src.modules.shared.infrastructure.tokens import InMemoryTokenBackend
from src.modules.shared.kernel.tokens import TokenManager


class TestSharedTokensLayering(unittest.IsolatedAsyncioTestCase):
    def test_layered_types_are_importable(self) -> None:
        self.assertTrue(callable(InMemoryTokenBackend))
        self.assertTrue(callable(TokenManager))

    async def test_token_manager_with_in_memory_backend_still_works(self) -> None:
        manager = TokenManager(InMemoryTokenBackend())

        await manager.set_token(
            prefix="otp",
            suffix="tenant-1",
            token="token-1",
            body={"value": "payload"},
            ttl=60,
        )

        payload = await manager.get_token(
            prefix="otp",
            suffix="tenant-1",
            token="token-1",
        )

        self.assertEqual(payload, {"value": "payload"})
