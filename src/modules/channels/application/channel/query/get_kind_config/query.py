from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetKindConfigQuery:
    """Передаёт параметры на чтение конфигурации выбранной платформы."""

    tenant_id: UUID
    kind: str
