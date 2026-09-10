from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


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
        """Откатывает текущую session."""
        ...


__all__ = ["UnitOfWorkProtocol"]
