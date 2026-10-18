from dataclasses import dataclass, field
from uuid import UUID
from src.modules.channels.application.plugin_contract import ReadPublicationPageInputDTO


@dataclass(frozen=True, slots=True)
class PreparePublicationInitializationResultDTO:
    """Фиксирует результат prepare_publication_initialization без пустого универсального DTO."""

    run_id: UUID
    actor_id: UUID
    channel_id: UUID
    connection_id: UUID
    generation: int
    platform_kind: str
    request: ReadPublicationPageInputDTO
    ciphertext: str = field(repr=False)
