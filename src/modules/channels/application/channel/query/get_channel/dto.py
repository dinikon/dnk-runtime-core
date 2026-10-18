from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetChannelResultDTO:
    """Возвращает проекцию сценария get_channel."""

    channel_id: UUID
    name: str
    platform_kind: str
    is_enabled: bool
    is_archived: bool
    revision: int
    connection_id: UUID | None
    verification_status: str | None
    is_paused: bool | None
