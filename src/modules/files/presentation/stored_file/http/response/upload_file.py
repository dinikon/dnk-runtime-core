from uuid import UUID
from pydantic import BaseModel
from src.modules.files.application.stored_file.command.upload_file.dto import (
    UploadFileResultDTO,
)


class UploadFileResponse(BaseModel):
    """HTTP-подтверждение операции upload_file, отдельное от Application DTO."""

    file_id: UUID
    name: str
    content_type: str
    size_bytes: int

    @classmethod
    def from_dto(cls, dto: UploadFileResultDTO) -> "UploadFileResponse":
        """Явно преобразует результат сценария без storage-секретов."""
        return cls(
            file_id=dto.file_id,
            name=dto.name,
            content_type=dto.content_type,
            size_bytes=dto.size_bytes,
        )
