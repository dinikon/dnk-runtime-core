from uuid import UUID

from pydantic import BaseModel


class AttachContactPointResponseSchema(BaseModel):
    contact_point_id: UUID
    binding_id: UUID
    contact_point_created: bool
    binding_created: bool
    already_attached: bool


__all__ = ["AttachContactPointResponseSchema"]
