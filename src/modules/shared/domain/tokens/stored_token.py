from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID


@dataclass(slots=True)
class StoredToken:
    """Сериализуемая запись token body и срока истечения."""

    body: dict[str, object]
    expires_at: datetime

    @classmethod
    def create(cls, body: dict[str, object], ttl_seconds: int) -> "StoredToken":
        """Создает StoredToken с expires_at относительно текущего UTC времени."""
        return cls(
            body=body,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )

    def is_expired(self) -> bool:
        """Проверяет, истек ли token на текущий момент UTC."""
        return datetime.now(UTC) >= self.expires_at

    def to_dict(self) -> dict[str, object]:
        """Сериализует token в JSON-compatible dict."""
        return {
            "body": _serialize_value(self.body),
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "StoredToken":
        """Восстанавливает StoredToken из JSON-compatible dict."""
        expires_at = payload["expires_at"]
        assert isinstance(expires_at, str)
        body = payload["body"]
        assert isinstance(body, dict)
        return cls(
            body=_deserialize_value(body),
            expires_at=datetime.fromisoformat(expires_at),
        )


def _serialize_value(value: object) -> object:
    """Рекурсивно сериализует datetime/UUID в JSON-compatible структуры."""
    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}
    if isinstance(value, UUID):
        return {"__type__": "uuid", "value": str(value)}
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _deserialize_value(value: object) -> object:
    """Рекурсивно восстанавливает datetime/UUID из serialized token body."""
    if isinstance(value, dict):
        value_type = value.get("__type__")
        if value_type == "datetime":
            raw_value = value["value"]
            assert isinstance(raw_value, str)
            return datetime.fromisoformat(raw_value)
        if value_type == "uuid":
            from uuid import UUID

            raw_value = value["value"]
            assert isinstance(raw_value, str)
            return UUID(raw_value)
        return {key: _deserialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deserialize_value(item) for item in value]
    return value
