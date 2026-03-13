from pydantic import BaseModel


class AddContactRequestSchema(BaseModel):
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
