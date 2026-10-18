from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListChannelsItemDTO:
    """Описывает строку списка каналов."""

    channel_id: UUID
    name: str
    platform_kind: str
    is_enabled: bool
    is_archived: bool
    revision: int
    connection_id: UUID | None
    verification_status: str | None
    is_paused: bool | None


@dataclass(frozen=True, slots=True)
class ListChannelsResultDTO:
    """Возвращает проекцию сценария list_channels."""

    items: tuple[ListChannelsItemDTO, ...]
    total: int
