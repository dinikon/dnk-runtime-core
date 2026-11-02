"""Вход вне-транзакционной проверки сохранённого доступа."""

from dataclasses import dataclass, field

from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckConnectionAccessCommand:
    """Передаёт снимок доступа и контекст попытки без инфраструктурных объектов."""

    platform_kind: str
    config: ConnectionConfigVO
    encrypted_credentials: bytes = field(repr=False)
    attempt: int
    max_attempts: int
