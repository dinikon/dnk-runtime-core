from uuid import UUID

from pydantic import BaseModel, Field


class UpdateCrmItemRequestSchema(BaseModel):
    objectId: UUID
    itemId: UUID
    fields: dict[str, str] = Field(default_factory=dict)
