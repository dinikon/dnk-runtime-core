from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

TENANT_SCHEMA_ALIAS = "tenant"


class Base(DeclarativeBase):
    """Базовый DeclarativeBase для глобальных SQLAlchemy-моделей."""

    __abstract__ = True
    metadata = MetaData()


class TenantBase(DeclarativeBase):
    """Базовый DeclarativeBase для tenant-scoped SQLAlchemy-моделей."""

    __abstract__ = True
    metadata = MetaData(schema=TENANT_SCHEMA_ALIAS)


PortableJSON = JSONB()
