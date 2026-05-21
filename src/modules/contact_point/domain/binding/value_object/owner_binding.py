from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class OwnerContactPointBinding:
    owner_object_id: EntityIdVO
    owner_record_id: EntityIdVO
