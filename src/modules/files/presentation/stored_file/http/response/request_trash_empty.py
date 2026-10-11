from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.modules.files.application.stored_file.command.request_trash_empty.dto import (
    RequestTrashEmptyResultDTO,
)


class RequestTrashEmptyResponse(BaseModel):
    """Подтверждает принятую фоновую очистку и её временную границу."""

    job_id: UUID
    cutoff: datetime

    @classmethod
    def from_dto(
        cls, result: RequestTrashEmptyResultDTO
    ) -> "RequestTrashEmptyResponse":
        """Преобразует конкретный Application DTO в самостоятельный HTTP-контракт."""
        return cls(job_id=result.job_id, cutoff=result.cutoff)
