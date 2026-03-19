from pydantic import BaseModel


class CreateContactRequestSchema(BaseModel):
    last_name: str
    first_name: str | None = None
    middle_name: str | None = None


__all__ = ["CreateContactRequestSchema"]
