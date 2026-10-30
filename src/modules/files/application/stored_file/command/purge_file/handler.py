from src.modules.files.application.stored_file.port.usage import FileUsagePort
from src.modules.files.application.bucket.location import storage_location
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.application.stored_file.command.purge_file.command import (
    PurgeFileCommand,
)
from src.modules.files.domain.bucket.repository import BucketRepositoryProtocol
from src.modules.files.domain.storage_provider.repository import (
    StorageProviderRepositoryProtocol,
)
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.domain.error import FileNotFoundError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PurgeFileHandler:
    """Удаляет регистрацию только после удаления всех версий owned-объекта."""

    def __init__(
        self,
        files: StoredFileRepositoryProtocol,
        buckets: BucketRepositoryProtocol,
        providers: StorageProviderRepositoryProtocol,
        storage: StorageResolverProtocol,
        usage: FileUsagePort,
    ) -> None:
        """Принимает порты одной внешней транзакции и приватного хранилища."""
        self._usage = usage
        self._files, self._buckets, self._providers, self._storage = (
            files,
            buckets,
            providers,
            storage,
        )

    async def execute(self, command: PurgeFileCommand) -> None:
        """Пропускает отсутствующую или устаревшую доставку, подтверждает текущее удаление."""
        try:
            file = await self._files.get_for_update(
                EntityIdVO.from_value(command.file_id)
            )
        except FileNotFoundError:
            return
        job_id = EntityIdVO.from_value(command.job_id)
        if not file.is_current_purge_job(job_id):
            return
        file.ensure_unused(
            in_use=bool(await self._usage.used(command.tenant_id, (file.id.uuid,)))
        )
        bucket = await self._buckets.get(file.bucket_id)
        bucket.ensure_ready()
        provider = await self._providers.get(bucket.provider_id)
        location = storage_location(command.tenant_id, bucket, provider)
        await self._storage.resolve(location).remove_owned_versions(
            location, file.object_key
        )
        file.mark_purged(job_id)
        await self._files.remove(file)
