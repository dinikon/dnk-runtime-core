from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PostgresCatalogMutationLock:
    """Transaction advisory lock общего порядка для Catalog одного tenant."""

    def __init__(self, session: AsyncSession) -> None:
        """Использует ту же сессию, что репозитории процесса."""
        self._session = session

    async def acquire(self, tenant_id: EntityIdVO) -> None:
        """Удерживает tenant Catalog lock до commit/rollback внешнего UoW."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"catalog:{tenant_id}"},
        )

    async def acquire_read(self, tenant_id: EntityIdVO) -> None:
        """Получает shared transaction lock; параллельные читатели не блокируют друг друга."""
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock_shared(hashtextextended(:key,0))"),
            {"key": f"catalog:{tenant_id}"},
        )
