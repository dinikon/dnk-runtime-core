from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AttachContactPointResultDTO:
    contact_point_id: UUID
    binding_id: UUID
    contact_point_created: bool
    binding_created: bool
    already_attached: bool


__all__ = ["AttachContactPointResultDTO"]
