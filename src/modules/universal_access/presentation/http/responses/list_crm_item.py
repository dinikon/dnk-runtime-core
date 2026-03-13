from uuid import UUID

from pydantic import BaseModel, Field


class ListCrmItemEntryResponseSchema(BaseModel):
    item_id: UUID
    fields: dict[str, str] = Field(default_factory=dict)


class ListCrmItemResponseSchema(BaseModel):
    items: list[ListCrmItemEntryResponseSchema] = Field(default_factory=list)
    page: int
    page_size: int
