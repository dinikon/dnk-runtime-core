import hashlib
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PostgresExchangeRatePublicationLock:
    """Удерживает распределённую xact-блокировку даже до первой строки книги."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        """Получает ту же сессию UoW, что и репозиторий книги."""
        self._session = session
        self._key = int.from_bytes(
            hashlib.sha256(
                f"dnk:currency:nbu:publication:{tenant_id}".encode()
            ).digest()[:8],
            signed=True,
        )

    async def acquire(self) -> None:
        """Блокирует публикацию до commit/rollback внешнего UoW."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": self._key}
        )
