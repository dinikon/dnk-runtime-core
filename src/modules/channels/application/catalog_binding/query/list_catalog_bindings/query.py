from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListCatalogBindingsQuery:
    """Конкретный вход сценария list_catalog_bindings."""

    catalog_root_id: UUID | None = None
    channel_id: UUID | None = None
    publication_id: UUID | None = None
    locale: str = "uk"
    offset: int = 0
    limit: int = 25
    mode: BindingMode | None = None
