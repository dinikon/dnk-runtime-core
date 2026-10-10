from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import uuid5
from src.modules.files.application.storage_provider.command.register_system_storage.command import (
    RegisterSystemStorageCommand,
)
from src.modules.files.application.storage_provider.command.register_system_storage.dto import (
    RegisterSystemStorageResultDTO,
)
from src.modules.files.domain.storage_provider.aggregate import StorageProvider
from src.modules.files.domain.storage_provider.repository import (
    StorageProviderRepositoryProtocol,
)
from src.modules.files.domain.bucket.aggregate import Bucket
from src.modules.files.domain.bucket.repository import BucketRepositoryProtocol
from src.modules.files.domain.value_object.bucket_name import BucketNameVO


class RegisterSystemStorageHandler:
    """Регистрирует системное подключение и намерение создать бакет без внешнего I/O."""

    def __init__(
        self,
        providers: StorageProviderRepositoryProtocol,
        buckets: BucketRepositoryProtocol,
    ) -> None:
        """Принимает репозитории общей tenant-транзакции."""
        self._providers, self._buckets = providers, buckets

    async def execute(
        self, command: RegisterSystemStorageCommand
    ) -> RegisterSystemStorageResultDTO:
        """Идемпотентно регистрирует MinIO и бакет; commit выполняет внешний процесс."""
        provider = await self._providers.get_system(for_registration=True)
        if provider is None:
            provider = StorageProvider.create(
                provider_id=EntityIdVO.from_value(
                    uuid5(command.tenant_id, "files.system.minio")
                ),
                name="MinIO",
                kind="minio",
                is_system=True,
                config_ref="system_minio",
            )
            await self._providers.add(provider)
        bucket = await self._buckets.get_system(provider.id)
        if bucket is None:
            bucket = Bucket.create(
                bucket_id=EntityIdVO.from_value(
                    uuid5(command.tenant_id, "files.system.bucket")
                ),
                provider_id=provider.id,
                name=BucketNameVO(f"dnk-tenant-{command.tenant_id.hex}"),
            )
            await self._buckets.add(bucket)
        return RegisterSystemStorageResultDTO(provider.id.uuid, bucket.id.uuid)
