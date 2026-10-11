from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.domain.bucket.repository import BucketRepositoryProtocol
from src.modules.files.domain.storage_provider.repository import (
    StorageProviderRepositoryProtocol,
)
from src.modules.files.domain.stored_file.error import FileStateConflictError
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.application.bucket.location import storage_location
from src.modules.files.application.stored_file.command.restore_file.command import (
    RestoreFileCommand,
)
from src.modules.files.application.stored_file.command.restore_file.dto import (
    RestoreFileResultDTO,
)


class RestoreFileHandler:
    """Восстанавливает файл только после проверки срока, диска и owned-объекта."""

    def __init__(
        self,
        files: StoredFileRepositoryProtocol,
        buckets: BucketRepositoryProtocol,
        providers: StorageProviderRepositoryProtocol,
        storage: StorageResolverProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает порты общей транзакции, storage и часы."""
        self._files, self._buckets, self._providers = files, buckets, providers
        self._storage, self._clock = storage, clock

    async def execute(self, command: RestoreFileCommand) -> RestoreFileResultDTO:
        """Делегирует переход Domain и сохраняет его лишь при доступном owned-объекте."""
        file = await self._files.get_for_update(EntityIdVO.from_value(command.file_id))
        file.ensure_can_restore(self._clock.now())
        bucket = await self._buckets.get(file.bucket_id)
        bucket.ensure_ready()
        provider = await self._providers.get(bucket.provider_id)
        location = storage_location(command.tenant_id, bucket, provider)
        if not await self._storage.resolve(location).exists_owned(
            location, file.object_key
        ):
            raise FileStateConflictError("File object no longer exists.")
        file.restore_from_trash(self._clock.now())
        await self._files.save(file)
        return RestoreFileResultDTO(file.id.uuid, file.status.value)
