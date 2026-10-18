from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateChannelResultDTO:
    """Возвращает результат сценария create_channel."""

    channel_id: UUID
    revision: int
    is_enabled: bool
