from pydantic import BaseModel
from uuid import UUID


class CurrentUserEmailResponseSchema(BaseModel):
    """Pydantic-схема email текущего пользователя."""

    id: UUID
    email: str
    is_primary: bool
    is_verified: bool
