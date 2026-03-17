from pydantic import BaseModel

from .contact_response import ContactResponseSchema


class ListContactsResponseSchema(BaseModel):
    items: list[ContactResponseSchema]
    limit: int
    offset: int
    count: int


__all__ = ["ListContactsResponseSchema"]
