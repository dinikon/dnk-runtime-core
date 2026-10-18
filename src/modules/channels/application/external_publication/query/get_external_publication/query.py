from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetExternalPublicationQuery:
    """Задаёт параметры чтения get_external_publication в доверенном tenant."""

    tenant_id: UUID
    publication_id: UUID
