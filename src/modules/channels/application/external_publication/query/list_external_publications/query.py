from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListExternalPublicationsQuery:
    """Задаёт параметры чтения list_external_publications в доверенном tenant."""

    tenant_id: UUID
    connection_id: UUID
    search: str | None = None
    stock_status: str | None = None
    offset: int = 0
    limit: int = 50
