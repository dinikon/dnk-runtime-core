from sqlalchemy import MetaData, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData()


StringUUID = String(64)
LongText = Text
