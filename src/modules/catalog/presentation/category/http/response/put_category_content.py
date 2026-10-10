from pydantic import BaseModel
from uuid import UUID


class PutCategoryContentResponse(BaseModel):
    """Подтверждённый результат конкретного сценария put_category_content."""

    id: UUID
    revision: int
