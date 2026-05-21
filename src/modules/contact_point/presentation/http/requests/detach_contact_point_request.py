from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DetachContactPointRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: UUID


__all__ = ["DetachContactPointRequestSchema"]
