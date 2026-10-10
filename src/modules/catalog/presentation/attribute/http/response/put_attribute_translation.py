from pydantic import BaseModel
from uuid import UUID


class PutAttributeTranslationResponse(BaseModel):
    """Подтверждённый результат конкретного сценария put_attribute_translation."""

    id: UUID
    revision: int
