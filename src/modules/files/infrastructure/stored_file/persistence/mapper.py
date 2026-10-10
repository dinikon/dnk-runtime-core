from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from typing import Any
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO


class StoredFileMapper:
    """Преобразует представление хранения без I/O и предметных правил."""

    @staticmethod
    def to_domain(row: StoredFileModel) -> StoredFile:
        """Восстанавливает агрегат через его явную фабрику."""
        return StoredFile.restore(
            file_id=EntityIdVO.from_value(row.id),
            bucket_id=EntityIdVO.from_value(row.bucket_id),
            object_key=row.object_key,
            name=FileNameVO(row.name),
            content_type=row.content_type,
            size=FileSizeVO(row.size_bytes),
            status=row.status,
            created_at=row.created_at,
            deleted_at=row.deleted_at,
            deleted_by=(
                EntityIdVO.from_value(row.deleted_by)
                if row.deleted_by is not None
                else None
            ),
            purge_after=row.purge_after,
            purge_requested_at=row.purge_requested_at,
            purge_job_id=(
                EntityIdVO.from_value(row.purge_job_id)
                if row.purge_job_id is not None
                else None
            ),
        )

    @staticmethod
    def to_insert_values(aggregate: StoredFile) -> dict[str, Any]:
        """Извлекает значения для записи без самостоятельного INSERT."""
        return {
            "id": aggregate.id.uuid,
            "bucket_id": aggregate.bucket_id.uuid,
            "object_key": aggregate.object_key,
            "name": aggregate.name.value,
            "content_type": aggregate.content_type,
            "size_bytes": aggregate.size.value,
            "status": aggregate.status.value,
            "created_at": aggregate.created_at,
            "deleted_at": aggregate.deleted_at,
            "deleted_by": (
                aggregate.deleted_by.uuid if aggregate.deleted_by is not None else None
            ),
            "purge_after": aggregate.purge_after,
            "purge_requested_at": aggregate.purge_requested_at,
            "purge_job_id": (
                aggregate.purge_job_id.uuid
                if aggregate.purge_job_id is not None
                else None
            ),
        }

    @staticmethod
    def to_update_values(aggregate: StoredFile) -> dict[str, Any]:
        """Извлекает сохраняемое состояние агрегата."""
        return StoredFileMapper.to_insert_values(aggregate)
