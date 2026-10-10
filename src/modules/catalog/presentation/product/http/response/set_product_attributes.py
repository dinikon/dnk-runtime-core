from uuid import UUID
from pydantic import BaseModel


class SetProductAttributesResponse(BaseModel):
    """Подтверждённый результат сценария set_product_attributes."""

    id: UUID
    revision: int
