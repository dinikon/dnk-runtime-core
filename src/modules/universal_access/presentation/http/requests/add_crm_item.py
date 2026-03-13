from uuid import UUID

from pydantic import BaseModel, Field


class AddCrmItemRequestSchema(BaseModel):
    objectId: UUID
    fields: dict[str, str] = Field(default_factory=dict)
