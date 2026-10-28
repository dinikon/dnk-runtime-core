from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.domain.catalog_binding.value_object import BindingMode


@dataclass(frozen=True, slots=True)
class ListPublicationBindingCandidatesQuery:
    """Конкретный вход сценария list_publication_binding_candidates."""

    channel_id: UUID
    mode: BindingMode
    locale: str = "uk"
    search: str = ""
    offset: int = 0
    limit: int = 25
