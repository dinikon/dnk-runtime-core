from dataclasses import dataclass, field
from uuid import UUID
from src.modules.channels.application.plugin_contract import (
    ReadPublicationDetailsInputDTO,
)


@dataclass(frozen=True, slots=True)
class PreparePublicationImportStepResultDTO:
    """Передаёт scoped сетевой intent между короткими UoW."""

    preparation_id: UUID
    actor_id: UUID
    connection_id: UUID
    platform_kind: str
    request: ReadPublicationDetailsInputDTO
    locales: tuple[str, ...]
    ciphertext: str = field(repr=False)
    image_id: str | None = None
    image_url: str | None = None
