import uuid

from sqlalchemy import TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class StringUUID(TypeDecorator):
    """SQLAlchemy TypeDecorator, хранящий UUID с совместимой нормализацией."""

    impl = PG_UUID
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Возвращает dialect-specific UUID descriptor."""
        return dialect.type_descriptor(PG_UUID(as_uuid=True))

    def process_bind_param(self, value, dialect):
        """Нормализует UUID перед записью в БД."""
        if value is None:
            return value
        return self._normalize_uuid(value)

    def process_result_value(self, value, dialect):
        """Нормализует UUID после чтения из БД."""
        if value is None:
            return value
        return self._normalize_uuid(value)

    @staticmethod
    def _normalize_uuid(value) -> uuid.UUID:
        """Приводит UUID или строковое значение к uuid.UUID."""
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


__all__ = ["StringUUID"]
