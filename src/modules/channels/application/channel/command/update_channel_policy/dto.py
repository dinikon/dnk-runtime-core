from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateChannelPolicyResultDTO:
    """Возвращает результат сценария update_channel_policy."""

    channel_id: UUID
    revision: int
