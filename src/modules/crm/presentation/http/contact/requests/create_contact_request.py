from pydantic import BaseModel


class CreateContactRequestSchema(BaseModel):
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None


__all__ = ["CreateContactRequestSchema"]
