from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListChannelsQuery:
    """Вход сценария чтения ListChannels."""

    tenant_id: UUID
    search: str = ""
    platform_kind: str | None = None
    status: str | None = None
    offset: int = 0
    limit: int = 50
