from pydantic import BaseModel, ConfigDict


class ExportCatalogStockRequest(BaseModel):
    """Синхронизирует связанную семью целиком без выбора отдельных позиций."""

    model_config = ConfigDict(extra="forbid")
