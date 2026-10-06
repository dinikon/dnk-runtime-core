from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.channels.application.publication_import_run.command.start_publication_import.dto import (
    StartPublicationImportResultDTO,
)


class StartPublicationImportResponse(BaseModel):
    """Определяет HTTP поля сценария start_publication_import для StartPublicationImportResultDTO."""

    run_id: UUID

    @classmethod
    def from_dto(cls, dto: StartPublicationImportResultDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            run_id=dto.run_id,
        )
