from uuid import UUID
from pydantic import BaseModel
from src.modules.files.application.bucket.query.list_buckets.dto import (
    BucketListItemDTO,
)


class ListBucketsItemResponse(BaseModel):
    """HTTP-проекция сценария list_buckets, отделённая от Application DTO."""

    id: UUID
    provider_id: UUID
    name: str
    status: str
    files_count: int
    size_bytes: int

    @classmethod
    def from_dto(cls, dto: BucketListItemDTO) -> "ListBucketsItemResponse":
        """Явно преобразует специализированный результат сценария."""
        return cls(
            id=dto.id,
            provider_id=dto.provider_id,
            name=dto.name,
            status=dto.status,
            files_count=dto.files_count,
            size_bytes=dto.size_bytes,
        )
