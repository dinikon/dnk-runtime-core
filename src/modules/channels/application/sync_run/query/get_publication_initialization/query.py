from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPublicationInitializationQuery:
    """Задаёт параметры чтения get_publication_initialization в доверенном tenant."""

    tenant_id: UUID
    connection_id: UUID
