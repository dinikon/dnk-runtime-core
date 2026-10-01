from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

TENANT_SCHEMA_ALIAS = "tenant"


class TenantBase(DeclarativeBase):
    """Базовый DeclarativeBase для tenant-scoped SQLAlchemy-моделей."""

    __abstract__ = True
    metadata = MetaData(schema=TENANT_SCHEMA_ALIAS)
