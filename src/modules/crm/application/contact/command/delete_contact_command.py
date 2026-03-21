from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class DeleteContactCommand:
    contact_id: EntityIdVO
