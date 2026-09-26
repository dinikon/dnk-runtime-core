from __future__ import annotations

import logging
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = logging.getLogger(__name__)


class UnitOfWork:
    """Request-scoped SQLAlchemy Unit of Work."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Сохраняет session factory для ленивого открытия session."""
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        """Возвращает активную SQLAlchemy session."""
        if self._session is None:
            raise RuntimeError(
                "UnitOfWork session is not available outside active context."
            )

        return self._session

    async def __aenter__(self) -> Self:
        """Открывает новую async session и возвращает UoW."""
        if self._session is not None:
            raise RuntimeError("UnitOfWork is already active.")

        self._session = self._session_factory()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Коммитит успешный context или откатывает при исключении."""
        session = self._session

        if session is None:
            raise RuntimeError("UnitOfWork is not active.")

        try:
            if exc_type is None:
                await self.commit()
            else:
                log.debug(
                    "UoW exit with exception -> rollback",
                    exc_info=(exc_type, exc, tb),
                )
                await self.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        """Коммитит текущую async session."""
        try:
            await self.session.commit()
        except BaseException:
            log.exception("UnitOfWork commit failed.")

            try:
                await self.session.rollback()
            except BaseException:
                log.exception("UnitOfWork rollback after failed commit also failed.")

            raise

    async def rollback(self) -> None:
        """Откатывает текущую async session."""
        await self.session.rollback()


__all__ = ["UnitOfWork"]
