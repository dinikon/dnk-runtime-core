from dataclasses import dataclass, field
from uuid import UUID
from src.modules.channels.application.plugin_contract import ResourceSettingsDTO


@dataclass(frozen=True, slots=True)
class PrepareConnectionVerificationResultDTO:
    """Фиксирует результат prepare_connection_verification без пустого универсального DTO."""

    channel_id: UUID
    connection_id: UUID
    generation: int
    platform_kind: str
    settings: ResourceSettingsDTO
    ciphertext: str = field(repr=False)
