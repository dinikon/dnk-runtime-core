from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.crm.application.company.command.update_company.dto import (
    UpdateCompanyResultDTO,
)


class PatchCompanyResponse(BaseModel):
    id: UUID
    legal_name: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: UpdateCompanyResultDTO) -> "PatchCompanyResponse":
        return cls(
            id=dto.id,
            legal_name=dto.legal_name,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
