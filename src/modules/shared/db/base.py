from sqlalchemy import JSON, MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData()


PortableJSON = JSON().with_variant(JSONB(), "postgresql")
