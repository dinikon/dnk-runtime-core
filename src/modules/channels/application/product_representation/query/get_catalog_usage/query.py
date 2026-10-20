from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetCatalogUsageQuery:
    """Задаёт конкретный вход сценария get_catalog_usage."""

    item_ids: tuple[UUID, ...]
