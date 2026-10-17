from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from datetime import UTC, datetime
from uuid import uuid4
from src.modules.files.application.stored_file.command.upload_file.command import (
    UploadFileCommand,
)
from src.modules.files.application.stored_file.command.upload_file.dto import (
    UploadFileResultDTO,
)
from src.modules.files.application.bucket.location import storage_location
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.domain.bucket.repository import BucketRepositoryProtocol
from src.modules.files.domain.storage_provider.repository import (
    StorageProviderRepositoryProtocol,
)
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.files.domain.error import StorageNotFoundError


class UploadFileHandler:
    """Загружает новый объект и сохраняет реестр в транзакции потребителя."""

    def __init__(
        self,
        providers: StorageProviderRepositoryProtocol,
        buckets: BucketRepositoryProtocol,
        files: StoredFileRepositoryProtocol,
        storage: StorageResolverProtocol,
    ) -> None:
        """Принимает порты одной tenant-транзакции, не управляя её commit."""
        self._providers, self._buckets, self._files, self._storage = (
            providers,
            buckets,
            files,
            storage,
        )

    async def execute(self, command: UploadFileCommand) -> UploadFileResultDTO:
        """Создаёт неизменяемый ключ и подтверждает фактический размер объекта."""
        if command.bucket_id is None:
            provider = await self._providers.get_system()
            if provider is None:
                raise StorageNotFoundError("System provider is not registered.")
            bucket = await self._buckets.get_system(provider.id)
            if bucket is None:
                raise StorageNotFoundError("System bucket is not registered.")
        else:
            bucket = await self._buckets.get(EntityIdVO.from_value(command.bucket_id))
            provider = await self._providers.get(bucket.provider_id)
        bucket.ensure_ready()
        file = StoredFile.create(
            file_id=EntityIdVO.from_value(uuid4()),
            bucket_id=bucket.id,
            name=FileNameVO(command.name),
            content_type=command.content_type,
            size=FileSizeVO(command.size_bytes),
            created_at=datetime.now(UTC),
        )
        await self._files.add(file)
        location = storage_location(command.tenant_id, bucket, provider)
        size = await self._storage.resolve(location).put(
            location,
            file.object_key,
            command.source,
            file.size.value,
            file.content_type,
        )
        file.mark_uploaded(size)
        await self._files.save(file)
        return UploadFileResultDTO(
            file.id.uuid, file.name.value, file.content_type, file.size.value
        )
