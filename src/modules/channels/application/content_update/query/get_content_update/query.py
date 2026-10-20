from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetContentUpdateQuery:
    """Передаёт доверенный контекст чтения конкретной операции."""

    tenant_id: UUID
    actor_id: UUID
    run_id: UUID
