from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.application.catalog_binding.contracts import BindingPairDTO


@dataclass(frozen=True, slots=True)
class PreviewCatalogBindingQuery:
    """Конкретный вход сценария preview_catalog_binding."""

    channel_id: UUID
    catalog_root_id: UUID
    mode: BindingMode
    publication_root_id: UUID | None
    items: tuple[BindingPairDTO, ...]
    group_id: UUID | None = None
    locale: str = "uk"
