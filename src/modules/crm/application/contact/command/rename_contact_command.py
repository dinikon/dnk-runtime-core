from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class RenameContactCommand:
    contact_id: EntityIdVO
    last_name: str
    first_name: str | None = None
    middle_name: str | None = None
