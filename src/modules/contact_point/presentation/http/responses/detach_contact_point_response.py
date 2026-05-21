from uuid import UUID

from pydantic import BaseModel


class DetachContactPointResponseSchema(BaseModel):
    contact_point_id: UUID
    binding_id: UUID
    binding_deleted: bool
    contact_point_deleted: bool
    contact_point_left_orphan: bool


__all__ = ["DetachContactPointResponseSchema"]
