from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

TENANT_SCHEMA_ALIAS = "tenant"


class Base(DeclarativeBase):
    """Базовый DeclarativeBase для глобальных SQLAlchemy-моделей."""

    __abstract__ = True
    metadata = MetaData()
