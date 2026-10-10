from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.application.bucket.command.provision_system_bucket.command import (
    ProvisionSystemBucketCommand,
)
from src.modules.files.application.bucket.command.provision_system_bucket.dto import (
    ProvisionSystemBucketResultDTO,
)
from src.modules.files.application.bucket.location import storage_location
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.domain.bucket.repository import BucketRepositoryProtocol
from src.modules.files.domain.storage_provider.repository import (
    StorageProviderRepositoryProtocol,
)
from src.modules.files.domain.error import InvalidStorageStateError


class ProvisionSystemBucketHandler:
    """Подготавливает приватный бакет после сохранения регистрации."""

    def __init__(
        self,
        providers: StorageProviderRepositoryProtocol,
        buckets: BucketRepositoryProtocol,
        storage: StorageResolverProtocol,
    ) -> None:
        """Принимает репозитории и независимый от SDK resolver."""
        self._providers, self._buckets, self._storage = providers, buckets, storage

    async def execute(
        self, command: ProvisionSystemBucketCommand
    ) -> ProvisionSystemBucketResultDTO:
        """Подтверждает владение, приватность и физическое существование контейнера."""
        bucket = await self._buckets.get(EntityIdVO.from_value(command.bucket_id))
        if bucket.status == "purged":
            raise InvalidStorageStateError("Bucket was purged.")
        provider = await self._providers.get(bucket.provider_id)
        location = storage_location(command.tenant_id, bucket, provider)
        await self._storage.resolve(location).ensure_private_bucket(location)
        bucket.mark_ready()
        await self._buckets.save(bucket)
        return ProvisionSystemBucketResultDTO(bucket.id.uuid, True)
