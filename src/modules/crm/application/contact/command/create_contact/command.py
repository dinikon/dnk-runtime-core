from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateContactCommand:
    """Намерение создать контакт от имени участника tenant."""

    actor_id: EntityIdVO
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
