from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListFunnelsQuery:
    """Вход чтения list процесса."""

    tenant_id: UUID
    model_key: str | None = None
    search: str = ""
    offset: int = 0
    limit: int = 50
