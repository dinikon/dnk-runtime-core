from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CatalogSelectionDTO:
    """Снимок выбранного товара в терминах CRM."""

    id: UUID
    name: str
    sku: str | None
    kind: str


class CatalogSelectionPort(Protocol):
    """Проверка внешней ссылки без доступа к SQL Catalog."""

    async def get(
        self, tenant_id: UUID, item_id: UUID, locale: str
    ) -> CatalogSelectionDTO:
        """Читает разрешённый снимок публичным сценарием Catalog."""
        ...
