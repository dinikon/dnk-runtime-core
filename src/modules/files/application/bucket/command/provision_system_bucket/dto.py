from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProvisionSystemBucketResultDTO:
    """Результат сценария provision_system_bucket; не является доменным агрегатом."""

    bucket_id: UUID
    ready: bool
