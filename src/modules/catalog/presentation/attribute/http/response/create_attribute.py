from pydantic import BaseModel
from uuid import UUID


class CreateAttributeResponse(BaseModel):
    """Подтверждённый результат конкретного сценария create_attribute."""

    id: UUID
    revision: int
