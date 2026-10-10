from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProviderListItemDTO:
    """Результат сценария list_providers; не является доменным агрегатом."""

    id: UUID
    name: str
    kind: str
    is_system: bool
