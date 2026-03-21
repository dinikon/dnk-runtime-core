from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class GetContactQuery:
    contact_id: EntityIdVO
