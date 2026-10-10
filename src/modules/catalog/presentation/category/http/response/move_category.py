from pydantic import BaseModel
from uuid import UUID


class MoveCategoryResponse(BaseModel):
    """Подтверждённый результат конкретного сценария move_category."""

    id: UUID
    revision: int
