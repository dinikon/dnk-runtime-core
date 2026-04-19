from uuid import UUID

from pydantic import BaseModel


class CurrentUserEmailResponseSchema(BaseModel):
    """Pydantic-схема email текущего пользователя."""

    id: UUID
    email: str
    is_primary: bool
    is_verified: bool


__all__ = ["CurrentUserEmailResponseSchema"]
