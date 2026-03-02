from sqlalchemy import JSON, MetaData, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData()


StringUUID = String(64)
LongText = Text
PortableJSON = JSON().with_variant(JSONB(), "postgresql")
