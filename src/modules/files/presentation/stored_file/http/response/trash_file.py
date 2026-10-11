from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from src.modules.files.application.stored_file.command.trash_file.dto import (
    TrashFileResultDTO,
)


class TrashFileResponse(BaseModel):
    """HTTP-подтверждение операции trash_file, отдельное от Application DTO."""

    file_id: UUID
    deleted_at: datetime
    purge_after: datetime

    @classmethod
    def from_dto(cls, dto: TrashFileResultDTO) -> "TrashFileResponse":
        """Явно преобразует результат сценария без storage-секретов."""
        return cls(
            file_id=dto.file_id,
            deleted_at=dto.deleted_at,
            purge_after=dto.purge_after,
        )
