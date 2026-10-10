from pydantic import BaseModel
from uuid import UUID


class ReplaceAttributeOptionsResponse(BaseModel):
    """Подтверждённый результат конкретного сценария replace_attribute_options."""

    id: UUID
    revision: int
