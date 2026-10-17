from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TrashFileCommand:
    """Намерение trash_file с доверенными tenant и инициатором."""

    tenant_id: UUID
    file_id: UUID
    actor_id: UUID
