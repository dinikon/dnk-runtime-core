from uuid import UUID

from pydantic import BaseModel


class DeleteCrmItemRequestSchema(BaseModel):
    objectId: UUID
    itemId: UUID
