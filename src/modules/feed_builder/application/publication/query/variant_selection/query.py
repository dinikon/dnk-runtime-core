from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VariantSelectionQuery:
    """Запрашивает фиксированный набор существующих вариантов для выбора."""

    feed_id: UUID
    catalog_item_id: UUID
    locale: str = "uk"
