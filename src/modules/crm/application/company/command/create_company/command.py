from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateCompanyCommand:
    actor_id: EntityIdVO
    legal_name: str
