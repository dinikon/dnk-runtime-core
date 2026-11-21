from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.channels.application.port.query_repository import (
    ChannelReadRow,
    ConnectionConfigReadRow,
    ResourceIdentityReadRow,
    VerificationReadRow,
)


@dataclass(frozen=True, slots=True)
class ListChannelItemDTO:
    """Публичные данные строки списка каналов."""

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
    recovery_required: bool
    available_capabilities: tuple[str, ...]

    @classmethod
    def from_read_row(cls, row: ChannelReadRow) -> "ListChannelItemDTO":
        """Явно выбирает публичные поля обогащённой проекции."""
        return cls(
            id=row.id,
            name=row.name,
            platform_kind=row.platform_kind,
            revision=row.revision,
            config=row.config,
            config_revision=row.config_revision,
            identity=row.identity,
            verification=row.verification,
            created_at=row.created_at,
            updated_at=row.updated_at,
            recovery_required=row.recovery_required,
            available_capabilities=row.available_capabilities,
        )


@dataclass(frozen=True, slots=True)
class ListChannelsDTO:
    """Страница результатов сценария чтения списка каналов."""

    items: tuple[ListChannelItemDTO, ...]
    total: int
    offset: int
    limit: int
