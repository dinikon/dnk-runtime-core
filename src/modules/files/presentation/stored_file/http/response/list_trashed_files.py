from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.modules.files.application.stored_file.file_category import FileCategory
from src.modules.files.application.stored_file.query.list_trashed_files.dto import (
    ListTrashedFilesItemDTO,
    ListTrashedFilesResultDTO,
)


class ListTrashedFilesItemResponse(BaseModel):
    """HTTP-строка корзины, отдельная от Application DTO."""

    file_id: UUID
    bucket_id: UUID
    bucket_name: str
    provider_id: UUID
    provider_name: str
    name: str
    content_type: str
    category: FileCategory
    size_bytes: int
    created_at: datetime
    status: str
    deleted_at: datetime
    purge_after: datetime
    purge_requested_at: datetime | None

    @classmethod
    def from_dto(cls, dto: ListTrashedFilesItemDTO) -> "ListTrashedFilesItemResponse":
        """Явно преобразует поля строки собственного сценария."""
        return cls(
            file_id=dto.file_id,
            bucket_id=dto.bucket_id,
            bucket_name=dto.bucket_name,
            provider_id=dto.provider_id,
            provider_name=dto.provider_name,
            name=dto.name,
            content_type=dto.content_type,
            category=dto.category,
            size_bytes=dto.size_bytes,
            created_at=dto.created_at,
            status=dto.status,
            deleted_at=dto.deleted_at,
            purge_after=dto.purge_after,
            purge_requested_at=dto.purge_requested_at,
        )


class ListTrashedFilesResponse(BaseModel):
    """HTTP-страница корзины с total и параметрами пагинации."""

    items: list[ListTrashedFilesItemResponse]
    total: int
    page: int
    page_size: int

    @classmethod
    def from_dto(cls, dto: ListTrashedFilesResultDTO) -> "ListTrashedFilesResponse":
        """Собирает страницу и преобразует каждую строку явно."""
        return cls(
            items=[ListTrashedFilesItemResponse.from_dto(item) for item in dto.items],
            total=dto.total,
            page=dto.page,
            page_size=dto.page_size,
        )
