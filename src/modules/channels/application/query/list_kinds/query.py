from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListKindsQuery:
    """Передаёт параметры на чтение каталога платформ для текущего tenant."""

    tenant_id: UUID
