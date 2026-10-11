from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RestoreFileCommand:
    """Намерение restore_file с доверенными tenant и инициатором."""

    tenant_id: UUID
    file_id: UUID
    actor_id: UUID
