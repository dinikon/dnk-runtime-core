from uuid import UUID
from pydantic import BaseModel


class CreateSimpleProductResponse(BaseModel):
    """Ответ HTTP-сценария create_simple_product."""

    id: UUID
    revision: int
    variant_id: UUID
