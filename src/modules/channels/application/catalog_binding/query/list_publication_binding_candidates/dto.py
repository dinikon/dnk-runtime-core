from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.catalog_binding.contracts import (
    BindingPositionDTO,
)


@dataclass(frozen=True, slots=True)
class ListPublicationBindingCandidatesResultDTO:
    """Результат сценария list_publication_binding_candidates."""

    items: tuple[BindingPositionDTO, ...]
    occupied_ids: tuple[UUID, ...]
    total: int
    offset: int
    limit: int
