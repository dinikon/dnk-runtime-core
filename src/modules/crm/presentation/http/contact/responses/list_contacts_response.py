from pydantic import BaseModel

from .contact_response import ContactResponseSchema


class ListContactsResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа со страницей контактов."""

    items: list[ContactResponseSchema]
    limit: int
    offset: int
    count: int


__all__ = ["ListContactsResponseSchema"]
