import os
from typing import Any, Literal
from urllib.parse import parse_qsl, quote_plus

from pydantic import Field, NonNegativeInt, PositiveInt, computed_field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    DB_HOST: str = Field(
        description="Hostname or IP address of the database server.",
        default="localhost",
    )

    DB_PORT: PositiveInt = Field(
        description="Port number for database connection.",
        default=5432,
    )

    DB_USERNAME: str = Field(
        description="Username for database authentication.",
        default="postgres",
    )

    DB_PASSWORD: str = Field(
        description="Password for database authentication.",
        default="",
    )

    DB_DATABASE: str = Field(
        description="Name of the database to connect to.",
        default="dniko",
    )

    DB_CHARSET: str = Field(
        description="Character set for database connection.",
        default="",
    )

    DB_EXTRAS: str = Field(
        description="Additional database connection parameters. Example: 'keepalives_idle=60&keepalives=1'",
        default="",
    )

    SQLALCHEMY_DATABASE_URI_SCHEME: str = Field(
        description="Database URI scheme for SQLAlchemy connection.",
        default="postgresql+asyncpg",
    )

    def _uses_sqlite(self) -> bool:
        return self.SQLALCHEMY_DATABASE_URI_SCHEME.startswith("sqlite")

    def _build_sqlite_database_uri(self) -> str:
        if self.DB_DATABASE == ":memory:":
            return f"{self.SQLALCHEMY_DATABASE_URI_SCHEME}:///{self.DB_DATABASE}"
        if os.path.isabs(self.DB_DATABASE):
            return (
                f"{self.SQLALCHEMY_DATABASE_URI_SCHEME}:////"
                f"{self.DB_DATABASE.lstrip('/')}"
            )
        return f"{self.SQLALCHEMY_DATABASE_URI_SCHEME}:///{self.DB_DATABASE}"

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self._uses_sqlite():
            return self._build_sqlite_database_uri()

        db_extras = (
            f"{self.DB_EXTRAS}&client_encoding={self.DB_CHARSET}"
            if self.DB_CHARSET
            else self.DB_EXTRAS
        ).strip("&")
        db_extras = f"?{db_extras}" if db_extras else ""
        return (
            f"{self.SQLALCHEMY_DATABASE_URI_SCHEME}://"
            f"{quote_plus(self.DB_USERNAME)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"
            f"{db_extras}"
        )

    SQLALCHEMY_POOL_SIZE: NonNegativeInt = Field(
        description="Maximum number of database connections in the pool.",
        default=30,
    )

    SQLALCHEMY_MAX_OVERFLOW: NonNegativeInt = Field(
        description="Maximum number of connections that can be created beyond the pool_size.",
        default=10,
    )

    SQLALCHEMY_POOL_RECYCLE: NonNegativeInt = Field(
        description="Number of seconds after which a connection is automatically recycled.",
        default=3600,
    )

    SQLALCHEMY_POOL_USE_LIFO: bool = Field(
        description="If True, SQLAlchemy will use last-in-first-out way to retrieve connections from pool.",
        default=False,
    )

    SQLALCHEMY_POOL_PRE_PING: bool = Field(
        description="If True, enables connection pool pre-ping feature to check connections.",
        default=False,
    )

    SQLALCHEMY_ECHO: bool | Literal["debug"] = Field(
        description="If True, SQLAlchemy will log all SQL statements.",
        default=False,
    )

    RETRIEVAL_SERVICE_EXECUTORS: NonNegativeInt = Field(
        description="Number of processes for the retrieval service, default to CPU cores.",
        default=os.cpu_count() or 1,
    )

    @computed_field
    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self) -> dict[str, Any]:
        if self._uses_sqlite():
            return {}

        db_extras_dict = dict(parse_qsl(self.DB_EXTRAS))

        server_settings: dict[str, str] = {
            **db_extras_dict,
            "timezone": "UTC",
        }

        connect_args = {"server_settings": server_settings}

        return {
            "pool_size": self.SQLALCHEMY_POOL_SIZE,
            "max_overflow": self.SQLALCHEMY_MAX_OVERFLOW,
            "pool_recycle": self.SQLALCHEMY_POOL_RECYCLE,
            "pool_pre_ping": self.SQLALCHEMY_POOL_PRE_PING,
            "connect_args": connect_args,
            "pool_use_lifo": self.SQLALCHEMY_POOL_USE_LIFO,
        }
