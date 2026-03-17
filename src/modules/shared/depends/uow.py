from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.shared.db.helper import db_helper
from modules.shared.db.uow import UnitOfWork, UnitOfWorkProtocol


async def get_uow(request: Request) -> AsyncGenerator[UnitOfWorkProtocol, None]:
    session_factory = getattr(request.app.state, "db", db_helper.session_factory)
    typed_session_factory: async_sessionmaker[AsyncSession] = session_factory
    async with UnitOfWork(typed_session_factory) as uow:
        yield uow


UoWDep = Annotated[UnitOfWorkProtocol, Depends(get_uow)]

__all__ = ["get_uow", "UoWDep"]
