from src.modules.files.application.stored_file.command.cleanup_orphaned_objects.command import (
    CleanupOrphanedObjectsCommand,
)
from src.modules.files.application.stored_file.command.cleanup_orphaned_objects.dto import (
    CleanupOrphanedObjectsResultDTO,
)
from src.modules.files.application.port.query_repository import (
    StorageQueryRepositoryProtocol,
)
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.application.bucket.location import storage_location
from src.modules.files.domain.bucket.repository import BucketRepositoryProtocol
from src.modules.files.domain.storage_provider.repository import (
    StorageProviderRepositoryProtocol,
)


class CleanupOrphanedObjectsHandler:
    """Удаляет старые объекты откатившихся загрузок, не анализируя бизнес-ссылки."""

    def __init__(
        self,
        providers: StorageProviderRepositoryProtocol,
        buckets: BucketRepositoryProtocol,
        repository: StorageQueryRepositoryProtocol,
        storage: StorageResolverProtocol,
    ) -> None:
        """Принимает порты зарегистрированных контейнеров и проверки реестра."""
        self._providers, self._buckets, self._repository, self._storage = (
            providers,
            buckets,
            repository,
            storage,
        )

    async def execute(
        self, command: CleanupOrphanedObjectsCommand
    ) -> CleanupOrphanedObjectsResultDTO:
        """Удаляет только принадлежащие модулю объекты вне защитного интервала."""
        removed = 0
        aborted = 0
        for bucket in await self._buckets.list_all():
            if bucket.status != "ready":
                continue
            provider = await self._providers.get(bucket.provider_id)
            location = storage_location(command.tenant_id, bucket, provider)
            adapter = self._storage.resolve(location)
            async for obj in adapter.objects(location):
                if (
                    obj.owned
                    and obj.modified_at < command.older_than
                    and not await self._repository.contains_key(bucket.id.uuid, obj.key)
                ):
                    await adapter.remove(location, obj.key)
                    removed += 1
            aborted += await adapter.abort_incomplete(location, command.older_than)
        return CleanupOrphanedObjectsResultDTO(removed, aborted)
