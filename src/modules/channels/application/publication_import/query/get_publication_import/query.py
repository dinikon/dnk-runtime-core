from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPublicationImportQuery:
    """Читает только подготовку текущего пользователя и tenant."""

    tenant_id: UUID
    actor_id: UUID
    preparation_id: UUID
