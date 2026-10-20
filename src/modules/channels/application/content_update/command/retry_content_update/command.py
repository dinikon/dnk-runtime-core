from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RetryContentUpdateCommand:
    """Передаёт версию конкретной операции и доверенного автора."""

    tenant_id: UUID
    actor_id: UUID
    run_id: UUID
    expected_revision: int
