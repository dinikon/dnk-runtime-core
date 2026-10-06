from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.channels.application.publication_import_run.query.get_publication_import_run.dto import (
    PublicationImportRunDetailsDTO,
)


class GetLatestPublicationImportResponse(BaseModel):
    """Определяет HTTP поля сценария get_latest_publication_import для PublicationImportRunDetailsDTO."""

    id: UUID
    channel_id: UUID
    status: str
    pages: int
    resources: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, dto: PublicationImportRunDetailsDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            id=dto.id,
            channel_id=dto.channel_id,
            status=dto.status,
            pages=dto.pages,
            resources=dto.resources,
            error_code=dto.error_code,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
