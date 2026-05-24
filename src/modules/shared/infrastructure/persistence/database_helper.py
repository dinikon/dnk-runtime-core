import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import src.modules.persistence  # noqa: F401
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import dnk_config
from src.modules.shared.infrastructure.persistence.base import Base
from src.modules.shared.infrastructure.persistence.database_startup_error import (
    DatabaseStartupError,
)

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

    @staticmethod
    def _is_retryable_startup_error(exc: Exception) -> bool:
        """Проверяет, стоит ли повторять startup-подключение к БД."""
        return isinstance(
            exc,
            (
                ConnectionError,
                ConnectionRefusedError,
                OSError,
                TimeoutError,
                OperationalError,
            ),
        )

    async def initialize_for_startup(self) -> None:
        """Пытается инициализировать схему БД с retry-политикой."""
        max_attempts = dnk_config.DB_STARTUP_MAX_ATTEMPTS
        retry_delay = dnk_config.DB_STARTUP_RETRY_DELAY_SECONDS

        for attempt in range(1, max_attempts + 1):
            try:
                await self.create_all()
                return
            except Exception as exc:
                is_retryable = self._is_retryable_startup_error(exc)
                is_last_attempt = attempt >= max_attempts

                if not is_retryable:
                    raise

                if is_last_attempt:
                    message = (
                        "Database startup failed after "
                        f"{max_attempts} attempts "
                        f"(host={dnk_config.DB_HOST}, port={dnk_config.DB_PORT}, database={dnk_config.DB_DATABASE}, "
                        f"retry_delay={retry_delay}s)."
                    )
                    log.error(
                        "%s Last error: %s: %s",
                        message,
                        type(exc).__name__,
                        exc,
                    )
                    raise DatabaseStartupError(message) from exc

                log.warning(
                    "Database is unavailable during startup (attempt %s/%s). "
                    "Retrying in %ss. Error: %s: %s",
                    attempt,
                    max_attempts,
                    retry_delay,
                    type(exc).__name__,
                    exc,
                )
                await asyncio.sleep(retry_delay)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Открывает async session context без автоматического commit."""
        async with self.session_factory() as session:
            yield session


db_helper = DatabaseHelper()
