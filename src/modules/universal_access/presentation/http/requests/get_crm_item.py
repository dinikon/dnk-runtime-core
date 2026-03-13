from uuid import UUID

from pydantic import BaseModel


class GetCrmItemRequestSchema(BaseModel):
    objectId: UUID
    itemId: UUID
