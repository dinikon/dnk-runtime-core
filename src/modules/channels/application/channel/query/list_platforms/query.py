from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListPlatformsQuery:
    """Задаёт параметры чтения list_platforms в доверенном tenant."""

    tenant_id: UUID
