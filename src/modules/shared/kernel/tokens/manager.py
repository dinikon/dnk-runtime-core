from __future__ import annotations

from src.modules.shared.kernel.tokens.models import StoredToken
from src.modules.shared.kernel.tokens.ports import TokenBackendProtocol


class TokenManager:
    def __init__(self, backend: TokenBackendProtocol):
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
        await self._backend.set(
            self._build_key(prefix=prefix, suffix=suffix, token=token),
            StoredToken.create(body=body, ttl_seconds=ttl),
        )

    async def exists(self, *, prefix: str, suffix: str, token: str) -> bool:
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
        stored = await self._backend.get(
            self._build_key(prefix=prefix, suffix=suffix, token=token)
        )
        if stored is None:
            return None
        return dict(stored.body)

    async def invalidate(self, *, prefix: str, suffix: str, token: str) -> None:
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
        key = self._build_key(prefix=prefix, suffix=suffix, token=token)
        stored = await self._backend.get(key)
        if stored is None:
            return None
        await self._backend.delete(key)
        return dict(stored.body)

    @staticmethod
    def _build_key(*, prefix: str, suffix: str, token: str) -> str:
        return f"{prefix}:{suffix}:{token}"
