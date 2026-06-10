from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateBroadcastCommand:
    """Команда создания broadcast definition в рамках tenant."""

    tenant_id: UUID | str
    title: str
    description: str | None
