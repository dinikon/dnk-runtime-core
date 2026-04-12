from pydantic import BaseModel


class UpdateContactRequestSchema(BaseModel):
    """Pydantic-схема тела запроса обновления контакта."""

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
    status: str | None = None
    tags: list[str] | None = None


__all__ = ["UpdateContactRequestSchema"]
