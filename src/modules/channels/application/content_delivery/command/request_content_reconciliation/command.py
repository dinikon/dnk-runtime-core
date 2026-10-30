from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestContentReconciliationCommand:
    """Вход конкретного сценария request_content_reconciliation."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    group_id: UUID
    publication_id: UUID
    expected_revision: int
