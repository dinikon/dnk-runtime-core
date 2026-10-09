from uuid import UUID
from pydantic import BaseModel


class PutProductTypeTranslationResponse(BaseModel):
    """Ответ HTTP-сценария put_product_type_translation."""

    id: UUID
    revision: int
