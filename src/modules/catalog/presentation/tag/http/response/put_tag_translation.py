from pydantic import BaseModel
from uuid import UUID


class PutTagTranslationResponse(BaseModel):
    """Подтверждённый результат конкретного сценария put_tag_translation."""

    id: UUID
    revision: int
