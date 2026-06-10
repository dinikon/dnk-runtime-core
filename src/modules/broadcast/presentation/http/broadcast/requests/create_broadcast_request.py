from pydantic import BaseModel


class CreateBroadcastRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания broadcast."""

    title: str
    description: str | None = None


__all__ = ["CreateBroadcastRequestSchema"]
