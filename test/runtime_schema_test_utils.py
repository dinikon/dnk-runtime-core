from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.modules.persistence  # noqa: F401
from src.modules.shared.db.base import Base


@asynccontextmanager
async def sqlite_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


@asynccontextmanager
async def sqlite_session_with_file() -> AsyncIterator[tuple[AsyncSession, str]]:
    with TemporaryDirectory() as tmpdir:
        database_path = Path(tmpdir) / "test.sqlite3"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as session:
                yield session, str(database_path)
        finally:
            await engine.dispose()


def new_uuid_str() -> str:
    return str(uuid4())

