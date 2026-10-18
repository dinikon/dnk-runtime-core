from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResumeConnectionCommand:
    """Передаёт намерение resume_connection с доверенным контекстом."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    revision: int
