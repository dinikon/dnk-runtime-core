from pydantic import BaseModel, Field


class CreateContactRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания контакта."""

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)


__all__ = ["CreateContactRequestSchema"]
