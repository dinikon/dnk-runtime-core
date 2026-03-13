from uuid import UUID

from pydantic import BaseModel


class ListCrmItemRequestSchema(BaseModel):
    objectId: UUID
    page: int = 1
    page_size: int = 50
