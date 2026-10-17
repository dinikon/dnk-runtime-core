from pydantic import BaseModel
from uuid import UUID


class SetCatalogItemMeasurementsResponse(BaseModel):
    """Отдельный HTTP-результат сценария set_catalog_item_measurements."""

    id: UUID
    revision: int
