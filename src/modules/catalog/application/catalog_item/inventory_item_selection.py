from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CatalogInventoryItemSelection:
    """Передаёт явное намерение выбрать, создать или очистить SKU."""

    mode: Literal["existing", "create", "clear"]
    inventory_item_id: UUID | None = None
    sku: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogInventoryItemReference:
    """Описывает результат разрешения ссылки в терминах потребителя Catalog."""

    id: UUID
    sku: str
    created: bool
