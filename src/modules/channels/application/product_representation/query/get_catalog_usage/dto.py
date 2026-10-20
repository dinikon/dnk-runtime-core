from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetCatalogUsageResultDTO:
    """Возвращает конкретный результат сценария get_catalog_usage."""

    item_ids: frozenset[UUID]
