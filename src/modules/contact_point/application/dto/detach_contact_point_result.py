from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DetachContactPointResultDTO:
    contact_point_id: UUID
    binding_id: UUID
    binding_deleted: bool
    contact_point_deleted: bool
    contact_point_left_orphan: bool


__all__ = ["DetachContactPointResultDTO"]
