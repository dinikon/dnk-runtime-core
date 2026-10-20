from dataclasses import dataclass, field
from uuid import UUID
from src.modules.channels.application.content_update.plugin_contract import (
    InspectContentUpdateInputDTO,
)


@dataclass(frozen=True, slots=True)
class PrepareContentUpdateStepResultDTO:
    """Передаёт worker только immutable вход одного сетевого шага."""

    publication_id: UUID
    connection_id: UUID
    platform_kind: str
    mode: str
    request: InspectContentUpdateInputDTO
    observed_hash: str | None
    ciphertext: str = field(repr=False)
