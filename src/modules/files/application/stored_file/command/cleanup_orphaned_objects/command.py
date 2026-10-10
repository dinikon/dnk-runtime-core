from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CleanupOrphanedObjectsCommand:
    """Вход сценария cleanup_orphaned_objects в доверенном tenant-контексте."""

    tenant_id: UUID
    older_than: datetime
