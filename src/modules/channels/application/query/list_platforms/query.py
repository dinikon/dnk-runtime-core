from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListPlatformsQuery:
    """Вход сценария чтения ListPlatforms."""

    tenant_id: UUID
