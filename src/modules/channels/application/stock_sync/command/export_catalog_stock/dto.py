from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ExportCatalogStockResultDTO:
    """Идентификаторы запланированных операций export_catalog_stock."""

    operation_ids: tuple[UUID, ...]
