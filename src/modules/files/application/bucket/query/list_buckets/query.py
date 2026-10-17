from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListBucketsQuery:
    """Вход сценария list_buckets в доверенном tenant-контексте."""

    tenant_id: UUID
    provider_id: UUID | None = None
