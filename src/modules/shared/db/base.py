from sqlalchemy import JSON, MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

TENANT_SCHEMA_ALIAS = "tenant"

class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData()

class TenantBase(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(schema=TENANT_SCHEMA_ALIAS)


PortableJSON = JSON().with_variant(JSONB(), "postgresql")
