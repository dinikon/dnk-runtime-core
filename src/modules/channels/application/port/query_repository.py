from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.channels.domain.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.types import JsonObject


@dataclass(frozen=True, slots=True)
class ConnectionConfigReadRow:
    """Публичные поля конфигурации для чтения и сериализации."""

    version: int
    endpoint: str
    settings: JsonObject


@dataclass(frozen=True, slots=True)
class ResourceIdentityReadRow:
    """Публичный идентификатор магазина без восстановления агрегата."""

    namespace: str
    key: str


@dataclass(frozen=True, slots=True)
class VerificationReadRow:
    """Публичная проекция проверки с примитивным ID задания."""

    job_id: UUID
    config_revision: int
    status: VerificationStatus
    checked_at: datetime | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class ChannelReadRow:
    """Публичная проекция карточки: секреты сюда не попадают."""

    id: UUID
    name: str
    platform_kind: str
    revision: int
    config: ConnectionConfigReadRow
    config_revision: int
    identity: ResourceIdentityReadRow | None
    verification: VerificationReadRow
    created_at: datetime
    updated_at: datetime
    recovery_required: bool = False
    available_capabilities: tuple[str, ...] = ()


class ChannelQueryRepository(Protocol):
    """Порт чтения готовых публичных проекций."""

    async def get(self, channel_id: UUID) -> ChannelReadRow | None:
        """Читает карточку текущего tenant."""
        ...

    async def list(
        self,
        search: str,
        platform_kind: str | None,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[ChannelReadRow, ...], int]:
        """Возвращает страницу и общее число каналов."""
        ...
