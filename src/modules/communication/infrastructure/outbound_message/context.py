from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.communication.application.outbound_message.processing import (
    OutboundProcessingByIdRepositoryProtocol,
)
from src.modules.shared.db.uow import UnitOfWork


class OutboundProcessingRepositoryContext:
    """UoW-backed context для обработки одного outbound message."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        repository_factory: Callable[
            [AsyncSession],
            OutboundProcessingByIdRepositoryProtocol,
        ],
    ) -> None:
        """Инициализирует context session factory и repository factory."""
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._uow: UnitOfWork | None = None

    async def __aenter__(self) -> OutboundProcessingByIdRepositoryProtocol:
        """Открывает UoW и возвращает repository для текущей transaction scope."""
        self._uow = UnitOfWork(self._session_factory)
        uow = await self._uow.__aenter__()
        assert uow.session is not None
        return self._repository_factory(uow.session)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Закрывает UoW с commit или rollback."""
        assert self._uow is not None
        await self._uow.__aexit__(exc_type, exc, tb)


class OutboundProcessingRepositoryContextFactory:
    """Фабрика transaction-scoped repository contexts для by-id processing."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        repository_factory: Callable[
            [AsyncSession],
            OutboundProcessingByIdRepositoryProtocol,
        ],
    ) -> None:
        """Инициализирует factory session и repository builder."""
        self._session_factory = session_factory
        self._repository_factory = repository_factory

    def __call__(self) -> OutboundProcessingRepositoryContext:
        """Создает новый context manager для processing operation."""
        return OutboundProcessingRepositoryContext(
            session_factory=self._session_factory,
            repository_factory=self._repository_factory,
        )


__all__ = [
    "OutboundProcessingRepositoryContext",
    "OutboundProcessingRepositoryContextFactory",
]
