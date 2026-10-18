from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProvisionSystemBucketCommand:
    """Вход сценария provision_system_bucket в доверенном tenant-контексте."""

    tenant_id: UUID
    bucket_id: UUID
