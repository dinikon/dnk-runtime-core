from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateTagCommand:
    """Вход создания tag с доверенным контекстом."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    locale: str
    label: str
