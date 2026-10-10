from pydantic import BaseModel
from uuid import UUID


class CreateTagResponse(BaseModel):
    """Подтверждённый результат конкретного сценария create_tag."""

    id: UUID
    revision: int
