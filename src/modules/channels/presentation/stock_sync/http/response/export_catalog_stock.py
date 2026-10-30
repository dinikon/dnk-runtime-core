from uuid import UUID

from pydantic import BaseModel


class ExportCatalogStockResponse(BaseModel):
    """Принятые операции export_catalog_stock."""

    operation_ids: tuple[UUID, ...]
