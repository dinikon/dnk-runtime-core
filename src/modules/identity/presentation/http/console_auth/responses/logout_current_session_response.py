from pydantic import BaseModel


class LogoutCurrentSessionResponseSchema(BaseModel):
    """Pydantic-схема ответа logout текущей session."""

    ok: bool


__all__ = ["LogoutCurrentSessionResponseSchema"]
