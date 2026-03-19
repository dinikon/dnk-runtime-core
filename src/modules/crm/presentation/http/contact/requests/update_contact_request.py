from pydantic import BaseModel


class UpdateContactRequestSchema(BaseModel):
    last_name: str
    first_name: str | None = None
    middle_name: str | None = None


__all__ = ["UpdateContactRequestSchema"]
