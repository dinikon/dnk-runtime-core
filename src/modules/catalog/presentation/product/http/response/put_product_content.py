from uuid import UUID
from pydantic import BaseModel


class PutProductContentResponse(BaseModel):
    """Ответ HTTP-сценария put_product_content."""

    id: UUID
    revision: int
