from uuid import UUID
from pydantic import BaseModel


class PutVariantContentResponse(BaseModel):
    """Ответ HTTP-сценария put_variant_content."""

    id: UUID
    revision: int
