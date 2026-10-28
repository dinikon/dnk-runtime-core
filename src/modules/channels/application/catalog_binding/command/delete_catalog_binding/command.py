from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DeleteCatalogBindingCommand:
    """Конкретный вход сценария delete_catalog_binding."""

    tenant_id: UUID
    channel_id: UUID
    group_id: UUID
    expected_revision: int
