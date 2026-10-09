from uuid import UUID
from pydantic import BaseModel


class ChangeProductTypeResponse(BaseModel):
    """Ответ HTTP-сценария change_product_type."""

    id: UUID
    revision: int
