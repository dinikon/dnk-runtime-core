from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый DeclarativeBase для глобальных SQLAlchemy-моделей."""

    __abstract__ = True
    metadata = MetaData()
