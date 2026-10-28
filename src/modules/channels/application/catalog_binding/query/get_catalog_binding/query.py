from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetCatalogBindingQuery:
    """Конкретный вход сценария get_catalog_binding."""

    channel_id: UUID
    group_id: UUID
    locale: str = "uk"
