import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import src.modules.persistence  # noqa: F401
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import dnk_config
from src.modules.shared.db.base import Base

log = logging.getLogger(__name__)


class DatabaseHelper:
    """Фасад создания engine/session factory и базовых DB lifecycle операций."""

    def __init__(self) -> None:
        """Инициализирует SQLAlchemy async engine и session factory из config."""
        self.engine: AsyncEngine = create_async_engine(
            dnk_config.SQLALCHEMY_DATABASE_URI,
            **dnk_config.SQLALCHEMY_ENGINE_OPTIONS,
            echo=dnk_config.SQLALCHEMY_ECHO,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        log.info("✅ Database initialized")

    async def dispose(self) -> None:
        """Закрывает async engine и освобождает DB resources."""
        await self.engine.dispose()
        log.info("Database engine disposed")

    async def create_all(self) -> None:
        """Создает все таблицы metadata Base через текущий engine."""
        async with self.engine.connect() as conn:
            async with conn.begin():
                await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Открывает async session context без автоматического commit."""
        async with self.session_factory() as session:
            yield session


db_helper = DatabaseHelper()
