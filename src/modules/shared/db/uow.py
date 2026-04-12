import logging
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = logging.getLogger(__name__)


class UnitOfWorkProtocol(Protocol):
    """Порт request-scoped Unit of Work с SQLAlchemy session."""

    session: AsyncSession

    async def __aenter__(self) -> "UnitOfWorkProtocol":
        """Открывает UoW context и возвращает себя."""
        ...

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Завершает UoW context с commit или rollback."""
        ...

    async def commit(self) -> None:
        """Фиксирует изменения текущей session."""
        ...

    async def rollback(self) -> None:
        """Откатывает изменения текущей session."""
        ...


class UnitOfWork:
    """Request-scoped SQLAlchemy Unit of Work."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """Сохраняет session factory для ленивого открытия session."""
        self.session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "UnitOfWork":
        """Открывает новую async session и возвращает UoW."""
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Коммитит успешный context или откатывает при исключении."""
        assert self.session is not None
        if exc_type:
            log.debug("UoW exit with exception -> rollback", exc_info=True)
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        """Коммитит текущую async session."""
        assert self.session is not None
        await self.session.commit()

    async def rollback(self) -> None:
        """Откатывает текущую async session."""
        assert self.session is not None
        await self.session.rollback()
