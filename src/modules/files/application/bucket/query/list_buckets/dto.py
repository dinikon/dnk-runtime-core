from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BucketListItemDTO:
    """Результат сценария list_buckets; не является доменным агрегатом."""

    id: UUID
    provider_id: UUID
    name: str
    status: str
    files_count: int
    size_bytes: int
