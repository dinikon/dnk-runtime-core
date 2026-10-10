from pydantic import BaseModel
from uuid import UUID


class CreateCategoryResponse(BaseModel):
    """Подтверждённый результат конкретного сценария create_category."""

    id: UUID
    revision: int
