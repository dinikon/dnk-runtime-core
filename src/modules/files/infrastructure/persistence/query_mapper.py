from collections.abc import Mapping
from typing import Any
from uuid import UUID
from src.modules.files.application.port.query_repository import FileContentLocationDTO
from src.modules.files.application.port.storage import StorageLocation
from src.modules.files.application.storage_provider.query.list_providers.dto import (
    ProviderListItemDTO,
)
from src.modules.files.application.bucket.query.list_buckets.dto import (
    BucketListItemDTO,
)


class StorageQueryMapper:
    """Преобразует SQL-проекции в специализированные DTO без I/O."""

    @staticmethod
    def to_provider(row: Mapping[str, Any]) -> ProviderListItemDTO:
        """Собирает безопасную строку подключения для Console."""
        return ProviderListItemDTO(
            row["id"], row["name"], row["kind"], row["is_system"]
        )

    @staticmethod
    def to_bucket(row: Mapping[str, Any]) -> BucketListItemDTO:
        """Собирает строку контейнера с агрегированной статистикой."""
        return BucketListItemDTO(
            row["id"],
            row["provider_id"],
            row["name"],
            row["status"],
            row["files_count"],
            row["size_bytes"],
        )

    @staticmethod
    def to_content_location(
        tenant_id: UUID, row: Mapping[str, Any]
    ) -> FileContentLocationDTO:
        """Собирает координаты готового файла без SDK и domain aggregate."""
        return FileContentLocationDTO(
            StorageLocation(
                tenant_id,
                row["bucket_id"],
                row["bucket_name"],
                row["kind"],
                row["config_ref"],
            ),
            row["object_key"],
            row["name"],
            row["content_type"],
            row["size_bytes"],
        )
