from uuid import UUID
from pydantic import BaseModel


class SetProductTagsResponse(BaseModel):
    """Подтверждённый результат сценария set_product_tags."""

    id: UUID
    revision: int
