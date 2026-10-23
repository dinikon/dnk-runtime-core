from datetime import datetime
from uuid import UUID
from src.modules.files.application.port.query_repository import (
    StorageQueryRepositoryProtocol,
    FileContentLocationDTO,
)
from src.modules.files.application.bucket.location import storage_location
from src.modules.files.domain.bucket.repository import BucketRepositoryProtocol
from src.modules.files.domain.storage_provider.repository import (
    StorageProviderRepositoryProtocol,
)
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.files.domain.error import (
    FileNotFoundError,
    StorageNotFoundError,
    InvalidFileError,
)
from src.modules.files.domain.stored_file.status import StoredFileStatus
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ArtifactFilesService:
    """Переиспользует реестр и Domain Files без вызова чужих обработчиков."""

    def __init__(
        self,
        files: StoredFileRepositoryProtocol,
        buckets: BucketRepositoryProtocol,
        providers: StorageProviderRepositoryProtocol,
        queries: StorageQueryRepositoryProtocol,
    ) -> None:
        """Получает порты одной внешней транзакции."""
        self.files, self.buckets, self.providers, self.queries = (
            files,
            buckets,
            providers,
            queries,
        )

    async def reserve(
        self,
        tenant_id: UUID,
        file_id: UUID,
        name: str,
        content_type: str,
        size: int,
        now: datetime,
    ) -> FileContentLocationDTO:
        """Создаёт регистрацию до сети; ID операции допускает безопасное восстановление."""
        provider = await self.providers.get_system()
        if provider is None:
            raise StorageNotFoundError("System provider is not registered.")
        bucket = await self.buckets.get_system(provider.id)
        if bucket is None:
            raise StorageNotFoundError("System bucket is not registered.")
        bucket.ensure_ready()
        try:
            file = await self.files.get_for_update(EntityIdVO(file_id))
        except FileNotFoundError:
            file = StoredFile.create(
                file_id=EntityIdVO(file_id),
                bucket_id=bucket.id,
                name=FileNameVO(name),
                content_type=content_type,
                size=FileSizeVO(size),
                created_at=now,
            )
            await self.files.add(file)
        if (
            file.bucket_id != bucket.id
            or file.size.value != size
            or file.name.value != name
            or file.content_type != content_type
            or file.status not in (StoredFileStatus.UPLOADING, StoredFileStatus.READY)
        ):
            raise InvalidFileError("Artifact identity changed.")
        return FileContentLocationDTO(
            storage_location(tenant_id, bucket, provider),
            file.object_key,
            name,
            content_type,
            size,
        )

    async def confirm(self, file_id: UUID, size: int) -> None:
        """Делает загруженный объект доступным читателям в транзакции владельца ссылки."""
        file = await self.files.get_for_update(EntityIdVO(file_id))
        if file.status == StoredFileStatus.READY and file.size.value == size:
            return
        file.mark_uploaded(size)
        await self.files.save(file)

    async def location(self, tenant_id: UUID, file_id: UUID) -> FileContentLocationDTO:
        """Не открывает поток до завершения SQL UoW."""
        result = await self.queries.content_location(tenant_id, file_id)
        if result is None:
            raise FileNotFoundError("Artifact is not available.")
        return result
