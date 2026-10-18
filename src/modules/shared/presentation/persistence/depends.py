from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.shared.infrastructure.persistence import UnitOfWork, db_helper


async def get_uow(request: Request) -> AsyncGenerator[UnitOfWork, None]:
    """Открывает общий UoW и завершает транзакцию до отправки HTTP-ответа."""

    session_factory = getattr(request.app.state, "db", db_helper.session_factory)
    connection = getattr(request.state, "tenant_connection", None)
    if connection is not None:
        session_factory = async_sessionmaker(connection, expire_on_commit=False)
    typed_session_factory: async_sessionmaker[AsyncSession] = session_factory
    async with UnitOfWork(typed_session_factory) as uow:
        yield uow


UoWDep = Annotated[UnitOfWork, Depends(get_uow, scope="function")]

__all__ = ["get_uow", "UoWDep"]
