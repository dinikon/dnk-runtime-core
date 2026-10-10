from uuid import UUID
from src.modules.files.domain.bucket.aggregate import Bucket
from src.modules.files.domain.storage_provider.aggregate import StorageProvider
from src.modules.files.application.port.storage import StorageLocation


def storage_location(
    tenant_id: UUID, bucket: Bucket, provider: StorageProvider
) -> StorageLocation:
    """Собирает согласованные координаты контейнера без обращения к инфраструктуре."""
    return StorageLocation(
        tenant_id, bucket.id.uuid, bucket.name.value, provider.kind, provider.config_ref
    )
