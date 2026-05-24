from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS


class TenantBase(DeclarativeBase):
    """Базовый DeclarativeBase для tenant-scoped SQLAlchemy-моделей."""

    __abstract__ = True
    metadata = MetaData(schema=TENANT_SCHEMA_ALIAS)
