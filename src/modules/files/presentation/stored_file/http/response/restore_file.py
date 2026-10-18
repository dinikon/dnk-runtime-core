from uuid import UUID
from pydantic import BaseModel
from src.modules.files.application.stored_file.command.restore_file.dto import (
    RestoreFileResultDTO,
)


class RestoreFileResponse(BaseModel):
    """HTTP-подтверждение операции restore_file, отдельное от Application DTO."""

    file_id: UUID
    status: str

    @classmethod
    def from_dto(cls, dto: RestoreFileResultDTO) -> "RestoreFileResponse":
        """Явно преобразует результат сценария без storage-секретов."""
        return cls(
            file_id=dto.file_id,
            status=dto.status,
        )
