from uuid import UUID
from pydantic import BaseModel


class SetProductCategoriesResponse(BaseModel):
    """Подтверждённый результат сценария set_product_categories."""

    id: UUID
    revision: int
