from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ListOwnerContactPointsRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_object_id: UUID
    owner_record_id: UUID


__all__ = ["ListOwnerContactPointsRequestSchema"]
