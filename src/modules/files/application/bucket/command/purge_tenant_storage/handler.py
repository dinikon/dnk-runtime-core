from src.modules.files.application.bucket.command.purge_tenant_storage.command import (
    PurgeTenantStorageCommand,
)
from src.modules.files.application.bucket.location import storage_location
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.domain.bucket.repository import BucketRepositoryProtocol
from src.modules.files.domain.storage_provider.repository import (
    StorageProviderRepositoryProtocol,
)


class PurgeTenantStorageHandler:
    """Очищает физические контейнеры перед удалением tenant-схемы."""

    def __init__(
        self,
        providers: StorageProviderRepositoryProtocol,
        buckets: BucketRepositoryProtocol,
        storage: StorageResolverProtocol,
    ) -> None:
        """Принимает порты; внешний процесс уже удерживает exclusive admission."""
        self._providers, self._buckets, self._storage = providers, buckets, storage

    async def execute(self, command: PurgeTenantStorageCommand) -> None:
        """Подтверждает удаление каждого контейнера; отсутствие допускает повтор."""
        for bucket in await self._buckets.list_all():
            provider = await self._providers.get(bucket.provider_id)
            location = storage_location(command.tenant_id, bucket, provider)
            await self._storage.resolve(location).purge(location)
            bucket.mark_purged()
            await self._buckets.save(bucket)
