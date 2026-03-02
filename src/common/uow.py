import logging
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = logging.getLogger(__name__)


class UnitOfWorkProtocol(Protocol):
    session: AsyncSession

    async def __aenter__(self) -> "UnitOfWorkProtocol": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class UnitOfWork:
    """Request-scoped SQLAlchemy Unit of Work."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self.session is not None
        if exc_type:
            log.debug("UoW exit with exception -> rollback", exc_info=True)
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        assert self.session is not None
        await self.session.commit()

    async def rollback(self) -> None:
        assert self.session is not None
        await self.session.rollback()
