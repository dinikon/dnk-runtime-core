import uuid

from sqlalchemy import CHAR, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class StringUUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        normalized_value = self._normalize_uuid(value)
        if dialect.name == "postgresql":
            return normalized_value
        return str(normalized_value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return self._normalize_uuid(value)

    @staticmethod
    def _normalize_uuid(value) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


__all__ = ["StringUUID"]
